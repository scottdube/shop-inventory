"""Import McMaster-Carr order history from parsed receipt emails.

Reads /tmp/mcm_orders.jsonl — one JSON object per receipt, produced by reading
the Receipt emails (the Confirmation and Shipped mails carry no line items).
See docs/mcmaster-import.md for the scope and the filter rules; the dealership
order is already excluded from that file and must stay excluded.

Creates FOUR things per line, and deliberately not a fifth:

  Part            with the McMaster number as IPN — canonical, unlike an ASIN
  SupplierPart    SKU = McMaster number, pack_quantity ALWAYS 1
  price break     per UNIT, not per pack
  StockItem       [ESTIMATE], NO stocktake date
  (no counts)     nothing here was counted; the B1/B2 walk does that

**Quantities are estimates and must stay that way.** These packs were bought
2021-2025 and have been drawn from ever since. Writing 4,072 units with a
stocktake date would assert a count nobody took. Every stock item goes in
[ESTIMATE] with `stocktake_date=None`, so the never-counted report keeps
surfacing all of them.

**Packs are converted to units** (README principle 2): "Packs of 50 at $12.36"
becomes 50 units at $0.2472 each, with the pack size in the notes.

**Never merged into existing parts** (README principle 19): grade is part
identity, and the cabinet-pack hardware already in A2 is ungraded. Matching is
by McMaster IPN only — if the IPN is absent, a new part is created even when
something similar exists. A human resolves duplicates afterwards.

**PO references** use InvenTree's own PO-NNNN. The vendor invoice goes in
`supplier_reference` and is the idempotency key — NOT the PO number, which is
neither unique (one order split across two invoices reuses it) nor stable (the
format is MMDD+name and repeats annually).

    itq run scripts/mcmaster_import.py            # dry run
    itq run scripts/mcmaster_import.py --commit
"""
import argparse, json, os, re, sys, django
from decimal import Decimal, ROUND_HALF_UP

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth import get_user_model
from company.models import Company, SupplierPart, SupplierPriceBreak
from order.models import PurchaseOrder, PurchaseOrderLineItem
from part.models import Part, PartCategory
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--src", default="/tmp/mcm_orders.jsonl")
a = ap.parse_args()

SUPPLIER = Company.objects.get(name="McMaster-Carr")
USER = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
NAME_MAX = 90          # Part.name caps at 100; leave room for a " [PN]" suffix

# --- category routing -------------------------------------------------------
# Ordered: first match wins. Anything unmatched lands in Hardware and is
# reported, so an unrouted class shows up rather than hiding.
ROUTES = [
    (r"\btap\b|\btaps\b|bur\b|tweezer|end mill|drill",            "Tooling"),
    (r"tubing|fitting|check valve|compression tube",              "Pneumatic"),
    (r"bearing|shaft collar|rod end|sprocket|pulley|v-belt|knob|"
     r"spring\b|springs\b|sleeve bearing",                        "Mechanical"),
    (r"tool steel|key stock|carbon steel (rod|hex bar)|"
     r"steel rod|hex bar|threaded rod",                           "Materials"),
    (r"screw|nut\b|nuts\b|washer|locknut|dowel pin|spring pin|"
     r"eyebolt|o-ring|sealing washer|steel ball",                 "Hardware"),
]
CATS = {n: PartCategory.objects.get(name=n, parent__isnull=True)
        for n in ("Hardware", "Mechanical", "Materials", "Pneumatic")}
CATS["Tooling"] = PartCategory.objects.get(pk=41)

# --- cabinet routing --------------------------------------------------------
# Scott, 2026-08-21: B1 is metric, B2 is imperial, and most of the hardware in
# them came from McMaster. Cabinet level only — the drawer is unknown until the
# walk, and a guessed drawer would be worse than an honest cabinet.
B1 = StockLocation.objects.get(name="B1")
B2 = StockLocation.objects.get(name="B2")
METRIC = re.compile(r"\bM\d+(\.\d+)?\s*x\s*[\d.]+\s*mm\b", re.I)
IMPERIAL = re.compile(r'\b\d+(/\d+)?"?-\d+\b|\b\d+-\d+\s+Thread\b')


def route_cat(desc):
    for pat, name in ROUTES:
        if re.search(pat, desc, re.I):
            return CATS[name], name
    return CATS["Hardware"], "Hardware (UNROUTED)"


def route_loc(desc, cat_name):
    if not cat_name.startswith("Hardware"):
        return None                      # only fasteners live in B1/B2
    if METRIC.search(desc):
        return B1
    if IMPERIAL.search(desc):
        return B2
    return None


def short_name(desc, pn):
    """A searchable name inside Part.name's 100-char cap.

    The cap is 100, not 200, and truncating AFTER appending a suffix eats the
    suffix — see TRAPS. Budget first, append second.
    """
    n = re.sub(r",\s*Packs? of \d+\s*$", "", desc.strip())
    if len(n) <= NAME_MAX:
        return n
    cut = n[:NAME_MAX].rsplit(" ", 1)[0]
    return cut.rstrip(" ,") + "…"


def per_unit(price_per_pack, pack_of):
    return (Decimal(str(price_per_pack)) / Decimal(pack_of)).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP)


orders = [json.loads(l) for l in open(a.src) if l.strip()]
print(f"source: {a.src}  ({len(orders)} orders, "
      f"{sum(len(o['lines']) for o in orders)} lines)\n")

# Guard: the dealership order must not be in this file.
bad = [o for o in orders if o.get("ship") != "Dover NH"]
if bad:
    print(f"REFUSING: {len(bad)} order(s) not shipped to the shop: "
          f"{[o['inv'] for o in bad]}")
    sys.exit(1)

next_ref = max([p.reference_int for p in PurchaseOrder.objects.all()] or [0])
cat_counts, loc_counts, made_parts, made_pos, skipped = {}, {}, 0, 0, []

for o in orders:
    existing = PurchaseOrder.objects.filter(
        supplier=SUPPLIER, supplier_reference=o["inv"]).first()
    if existing:
        skipped.append(f"PO for invoice {o['inv']} already exists ({existing.reference})")
        continue

    if a.commit:
        # Create PLACED, add lines, and only then move to Complete via
        # queryset .update(). A completed PO is LOCKED: save() raises
        # "This order is locked and cannot be modified" and lines cannot be
        # added. Status goes last, and never through save(). See TRAPS.
        next_ref += 1
        po = PurchaseOrder.objects.create(
            supplier=SUPPLIER, reference=f"PO-{next_ref:04d}",
            supplier_reference=o["inv"], issue_date=o["date"], status=20,
            description=f"McMaster-Carr order {o['date']}"[:250],
            notes=(f"Imported from the McMaster receipt email 2026-08-21.\n\n"
                   f"Vendor PO string: {o['po']}. Invoice {o['inv']} is the "
                   f"idempotency key — the PO string is neither unique (a "
                   f"split shipment reuses it) nor stable (MMDD+name repeats "
                   f"annually).\n\nOrder total ${o['total']:.2f} including "
                   f"shipping; line prices below are merchandise only."))
        made_pos += 1
    else:
        po = None

    for ln in o["lines"]:
        pn, desc = ln["pn"], ln["desc"]
        units = ln["packs"] * ln["pack_of"]
        unit_price = per_unit(ln["price_per_pack"], ln["pack_of"])
        cat, cat_name = route_cat(desc)
        loc = route_loc(desc, cat_name)
        cat_counts[cat_name] = cat_counts.get(cat_name, 0) + 1
        lk = loc.name if loc else "(no location)"
        loc_counts[lk] = loc_counts.get(lk, 0) + 1

        if not a.commit:
            continue

        p = Part.objects.filter(IPN=pn).first()
        if p is None:
            nm = short_name(desc, pn)
            if Part.objects.filter(name=nm).exists():
                nm = f"{nm} [{pn}]"[:100]
            p = Part.objects.create(
                name=nm, IPN=pn, category=cat, description=desc[:250],
                active=True, component=True, purchaseable=True,
                keywords=f"mcmaster {pn} " + " ".join(
                    re.findall(r"[A-Za-z0-9/\"\.-]{3,}", desc.lower())[:20]))
            p.notes = (
                f"**McMaster-Carr {pn}** — imported from order history "
                f"2026-08-21.\n\nFull vendor description:\n\n> {desc}\n\n"
                f"Sold in packs of {ln['pack_of']}; stocked per UNIT at "
                f"${unit_price} each (README principle 2 — pack_quantity is "
                f"always 1).\n\n**Never merged into an existing part.** Grade "
                f"is part identity and the cabinet-pack hardware in A2 is "
                f"ungraded; matching here is by McMaster IPN only. If a "
                f"similar ungraded part exists, they are two parts.\n\n"
                f"Full specs and CAD are on McMaster's site under this number, "
                f"which is canonical and stable.")
            if loc:
                p.default_location = loc
            p.save()
            made_parts += 1

        sp = SupplierPart.objects.filter(supplier=SUPPLIER, SKU=pn).first()
        if sp is None:
            sp = SupplierPart.objects.create(
                part=p, supplier=SUPPLIER, SKU=pn, pack_quantity="1",
                link=f"https://www.mcmaster.com/{pn}/",
                note=f"Sold in packs of {ln['pack_of']}")
        if not SupplierPriceBreak.objects.filter(part=sp, quantity=1).exists():
            SupplierPriceBreak.objects.create(part=sp, quantity=1, price=unit_price,
                                              price_currency="USD")

        PurchaseOrderLineItem.objects.create(
            order=po, part=sp, quantity=units, received=units,
            purchase_price=unit_price, purchase_price_currency="USD",
            notes=(f"Line {ln['n']}: {ln['packs']} pack(s) of {ln['pack_of']} "
                   f"at ${ln['price_per_pack']:.2f}/pack = {units} units")[:250])

        si = StockItem.objects.create(
            part=p, location=loc, quantity=units,
            purchase_price=unit_price, purchase_price_currency="USD")
        si.stocktake_date = None
        si.notes = (
            f"[ESTIMATE] Quantity is what was PURCHASED on {o['date']} "
            f"({ln['packs']} pack(s) of {ln['pack_of']}), not a count. Bought "
            f"between 2021 and 2025 and drawn from since — the real figure is "
            f"almost certainly lower. No stocktake date on purpose, so the "
            f"never-counted report keeps surfacing this. Correct it on the "
            f"B1/B2 walk.")
        si.save()

    if a.commit and po is not None:
        # Lines are in; close the order. queryset .update() bypasses save(),
        # which would try to consume allocations we deliberately do not have.
        PurchaseOrder.objects.filter(pk=po.pk).update(status=30)

print("=== category routing ===")
for k, v in sorted(cat_counts.items(), key=lambda x: -x[1]):
    print(f"  {k:26} {v:3}")
print("\n=== stock location routing ===")
for k, v in sorted(loc_counts.items(), key=lambda x: -x[1]):
    print(f"  {k:26} {v:3}")
if skipped:
    print("\n=== skipped (already imported) ===")
    for s in skipped:
        print(f"  {s}")

if not a.commit:
    print("\nDRY RUN — nothing written")
    sys.exit(0)

# ---- verify by re-reading ----
print(f"\n=== verify ===")
fail = []


def chk(label, ok, detail=""):
    print(f'  {"ok  " if ok else "FAIL"} {label}' + (f"  ({detail})" if detail else ""))
    if not ok:
        fail.append(label)


pos = PurchaseOrder.objects.filter(supplier=SUPPLIER)
chk(f"{len(orders)} POs exist", pos.count() == len(orders), f"{pos.count()}")
chk("every PO keyed on its invoice",
    all(p.supplier_reference for p in pos))
ipns = {ln["pn"] for o in orders for ln in o["lines"]}
found = Part.objects.filter(IPN__in=ipns).count()
chk(f"{len(ipns)} parts by IPN", found == len(ipns), f"{found}")
sps = SupplierPart.objects.filter(supplier=SUPPLIER).count()
chk(f"{len(ipns)} supplier parts", sps == len(ipns), f"{sps}")
chk("all supplier parts pack_quantity=1",
    not SupplierPart.objects.filter(supplier=SUPPLIER).exclude(pack_quantity="1").exists())
si = StockItem.objects.filter(part__IPN__in=ipns)
chk("no stock item carries a stocktake date",
    not si.exclude(stocktake_date=None).exists())
chk("every stock item marked [ESTIMATE]",
    si.count() == si.filter(notes__startswith="[ESTIMATE]").count(),
    f"{si.filter(notes__startswith='[ESTIMATE]').count()}/{si.count()}")

print(f"\nparts created {made_parts}, POs created {made_pos}")
print("WROTE and verified" if not fail else f"VERIFY FAILED on {len(fail)}")
sys.exit(1 if fail else 0)
