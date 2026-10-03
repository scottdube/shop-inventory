"""Import Bambu Lab order history as PURCHASE HISTORY ONLY: no stock rows.

Reads a JSON file of transcribed order confirmations (see docs/bambu-import.md).
The data stays in the PRIVATE ~/code repo because it carries order numbers.
Push it to the Mini first:

    itq push ~/code/scripts/bambu_orders_1003.json /tmp/bambu_orders.json
    itq run scripts/bambu_import.py            # dry run
    itq run scripts/bambu_import.py --commit

Creates Part, SupplierPart (SKU = code + form), price break, and a COMPLETE
PO per order, with lines marked received. **Creates no StockItem.** Scott,
2026-10-03: importing orders as stock would put three years of printed-away
filament on the shelf. The McMaster importer books purchases as [ESTIMATE]
stock, and that pattern is deliberately NOT copied here. Stock comes only from
a physical count at each site.

PO `destination` records the ship-to site (SLN/LRD). That is provenance, not
current location: spools have moved between sites, and nobody recorded which.

Idempotent: a PO is keyed on the vendor order number (`supplier_reference`), a
part on its Bambu SupplierPart SKU.
"""
import argparse, json, os, sys, django
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart, SupplierPriceBreak
from order.models import PurchaseOrder, PurchaseOrderLineItem, PurchaseOrderExtraLine
from part.models import Part, PartCategory
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--src", default="/tmp/bambu_orders.json")
a = ap.parse_args()

orders = sorted(json.load(open(a.src))["orders"], key=lambda o: o["date"])
SUPPLIER = Company.objects.get(pk=29, name="Bambu Lab")
SITE = {"SLN": StockLocation.objects.get(name="SLN", parent=None),
        "LRD": StockLocation.objects.get(name="LRD", parent=None)}
TODAY = "2026-10-03"

# kind -> (parent path, leaf name)
CATS = {"filament": ("Shop/Consumables", "Filament"),
        "bundle": ("Shop/Consumables", "Filament"),
        "printer_part": ("Shop/Accessories", "3D Printer"),
        "printer": ("Equipment", "3D Printers")}


def money(x):
    return Decimal(str(x)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def category(kind):
    parent_path, leaf = CATS[kind]
    parent = PartCategory.objects.get(pathstring=parent_path)
    c = PartCategory.objects.filter(parent=parent, name=leaf).first()
    if c is None and a.commit:
        c = PartCategory.objects.create(parent=parent, name=leaf, description={
            "Filament": "3D printer filament. Counted in SPOOLS (or boxes), not kg. "
                        "Part identity is Bambu code + form: refill and with-spool are two parts.",
            "3D Printer": "Hotends, build plates, glue, AMS spares and printer hardware.",
            "3D Printers": "Printers. One-of equipment, not consumable stock.",
        }[leaf])
    return c


# ---- 1. refuse anything that does not reconcile -----------------------------
bad = []
for o in orders:
    s = round(sum(l["ext"] for l in o["lines"]), 2)
    if abs(s - o["subtotal"]) >= 0.02:
        bad.append(f"{o['order']}: lines {s} != subtotal {o['subtotal']}")
if bad:
    print("REFUSED: transcription does not reconcile\n  " + "\n  ".join(bad))
    sys.exit(2)

# ---- 2. plan ----------------------------------------------------------------
skus = {}
for o in orders:
    for l in o["lines"]:
        skus.setdefault(l["sku"], l)
existing_po = {p.supplier_reference for p in PurchaseOrder.objects.filter(supplier=SUPPLIER)}
existing_sp = {s.SKU for s in SupplierPart.objects.filter(supplier=SUPPLIER)}
print(f"orders {len(orders)} ({sum(o['order'] in existing_po for o in orders)} already imported)")
print(f"SKUs   {len(skus)} ({sum(k in existing_sp for k in skus)} already exist)")
by_kind = defaultdict(list)
for k, l in skus.items():
    by_kind[l["kind"]].append(l["name"])
for kind, names in by_kind.items():
    print(f"\n  {kind} -> {'/'.join(CATS[kind])}  ({len(names)})")
    for n in sorted(names):
        print(f"    {n}")
for o in orders:
    print(f"\n{o['date']} {o['site']} ${o['subtotal']:.2f}  {len(o['lines'])} lines")

if not a.commit:
    print("\nDRY RUN: nothing written")
    sys.exit(0)

# ---- 3. write ----------------------------------------------------------------
next_ref = max([p.reference_int for p in PurchaseOrder.objects.all()] or [0])
made_parts = made_pos = 0
history = defaultdict(list)          # sku -> [(date, site, qty, unit)]

for o in orders:
    for l in o["lines"]:
        history[l["sku"]].append((o["date"], o["site"], l["qty"], money(l["ext"] / l["qty"])))

for sku, l in skus.items():
    sp = SupplierPart.objects.filter(supplier=SUPPLIER, SKU=sku).first()
    if sp is not None:
        continue
    cat = category(l["kind"])
    name = l["name"][:100]
    if Part.objects.filter(name=name).exists():
        name = f"{name} [{sku}]"[:100]
    p = Part.objects.create(
        name=name, IPN=l.get("code") or None, category=cat,
        description=l["name"][:250], active=True, purchaseable=True,
        component=False, keywords=f"bambu {sku.lower()} {l.get('code', '')}".strip())
    lines = "\n".join(f"- {d} -> {s}: {q} @ ${u}" for d, s, q, u in history[sku])
    notes = [f"**Bambu Lab, SKU `{sku}`**. Imported from order history {TODAY}.",
             "",
             "**No stock row on purpose.** These are purchases, not a count: filament "
             "gets printed away, and spools moved between SLN and LRD without a record. "
             "Stock comes from a physical count only.",
             "",
             "Bought (date -> ship-to site: qty @ unit price paid):", lines]
    if l.get("code_src") == "inferred":
        notes += ["", f"Code {l['code']} INFERRED: the 2023 email gave no numeric code, so it "
                      "was taken from a later order of the same colour."]
    if l.get("note"):
        notes += ["", l["note"]]
    if l["kind"] == "bundle":
        notes += ["", "A BUNDLE is one unit, not a multipack (TECHNIQUES/README: an assortment "
                      "is not a pack). Once opened, its rolls are counted under their own "
                      "colour parts."]
    if l["kind"] == "printer":
        notes += ["", "Equipment, not stock. The ship-to address is only where it ARRIVED; "
                      "set its location from where it actually stands."]
    p.notes = "\n".join(notes)
    p.save()
    made_parts += 1

    sp = SupplierPart(part=p, supplier=SUPPLIER, SKU=sku,
                      pack_quantity=str(l.get("pack", 1)),
                      link="https://us.store.bambulab.com/",
                      note="SKU is ours (code + form); Bambu's store uses its own variant IDs.")
    sp.save()   # through save(): pack_quantity_native is derived in clean() (TRAPS)

for o in orders:
    if PurchaseOrder.objects.filter(supplier=SUPPLIER, supplier_reference=o["order"]).exists():
        continue
    next_ref += 1
    po = PurchaseOrder.objects.create(
        supplier=SUPPLIER, reference=f"PO-{next_ref:04d}",
        supplier_reference=o["order"], issue_date=o["date"], status=20,
        destination=SITE[o["site"]],
        description=f"Bambu Lab order {o['date']}, shipped to {o['site']}"[:250],
        notes=(f"Imported {TODAY} from the Bambu order confirmation email. **Purchase "
               f"history only: receiving this order created NO stock.** Destination "
               f"{o['site']} is where it was SHIPPED, not where it is now.\n\n"
               f"Subtotal ${o['subtotal']:.2f}."
               + (f"\n\n{o['discount_note']}" if o.get("discount_note") else "")))
    made_pos += 1
    for l in o["lines"]:
        sp = SupplierPart.objects.get(supplier=SUPPLIER, SKU=l["sku"])
        PurchaseOrderLineItem.objects.create(
            order=po, part=sp, quantity=l["qty"], received=l["qty"],
            purchase_price=money(l["ext"] / l["qty"]), purchase_price_currency="USD",
            notes=f"{l['name']}: {l['qty']} @ ${l['ext']:.2f} extended"[:250])
    for ref, amt in (("Shipping", o.get("shipping", 0)), ("Sales tax", o.get("tax", 0))):
        if amt:
            PurchaseOrderExtraLine.objects.create(order=po, reference=ref, quantity=1,
                                                  price=money(amt), price_currency="USD")
    # A COMPLETE PO is locked to save(); move status by queryset (house pattern).
    PurchaseOrder.objects.filter(pk=po.pk).update(status=30, complete_date=o["date"])

# price break = latest unit price paid
for sku, h in history.items():
    sp = SupplierPart.objects.get(supplier=SUPPLIER, SKU=sku)
    latest = sorted(h)[-1][3]
    pb = SupplierPriceBreak.objects.filter(part=sp, quantity=1).first()
    if pb is None:
        SupplierPriceBreak.objects.create(part=sp, quantity=1, price=latest, price_currency="USD")
    elif pb.price.amount != latest:
        pb.price = latest
        pb.save()

# ---- 4. verify by re-reading --------------------------------------------------
print("\n=== verify ===")
fail = []


def chk(label, ok, detail=""):
    print(f'  {"ok  " if ok else "FAIL"} {label}' + (f"  ({detail})" if detail else ""))
    if not ok:
        fail.append(label)


pos = PurchaseOrder.objects.filter(supplier=SUPPLIER)
chk(f"{len(orders)} Bambu POs", pos.count() == len(orders), pos.count())
for o in orders:
    po = pos.filter(supplier_reference=o["order"]).first()
    if po is None:
        chk(f"{o['order']} exists", False)
        continue
    s = sum(ln.quantity * ln.purchase_price.amount for ln in po.lines.all())
    chk(f"{po.reference} {o['date']} {o['site']} complete, lines = subtotal",
        po.status == 30 and abs(float(s) - o["subtotal"]) < 0.02
        and po.destination_id == SITE[o["site"]].pk
        and all(ln.received == ln.quantity for ln in po.lines.all()),
        f"status {po.status}, ${float(s):.2f}, dest {po.destination}")
sps = SupplierPart.objects.filter(supplier=SUPPLIER)
chk(f"{len(skus)} supplier parts", sps.count() == len(skus), sps.count())
chk("every supplier part has a part and a price break",
    all(sp.part_id and sp.pricebreaks.exists() for sp in sps))
aa = sps.filter(SKU="AA187").first()
chk("AA187 pack is 20 in BOTH fields",
    aa is not None and float(aa.pack_quantity_native) == 20 and aa.pack_quantity == "20",
    f"{aa.pack_quantity!r}/{aa.pack_quantity_native}" if aa else "missing")
n_stock = StockItem.objects.filter(part__in=[sp.part_id for sp in sps]).count()
chk("NO stock rows on any Bambu part", n_stock == 0, n_stock)

print(f"\nparts created {made_parts}, POs created {made_pos}")
print("WROTE and verified" if not fail else f"VERIFY FAILED on {len(fail)}")
sys.exit(1 if fail else 0)
