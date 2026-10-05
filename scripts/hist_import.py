"""Historical tooling orders -> closed POs + [ESTIMATE] stock. Data-driven.

Written 2026-10-04 for docs/tooling-inventory.md. Scott: *"put estimated counts
from what was purchased, it will have to be inventoried as stuff has been damaged
or destroyed and disposed of over time."*

    itq push data/tooling/lakeshore.json /tmp/hist_lakeshore.json
    itq run scripts/hist_import.py /tmp/hist_lakeshore.json            # dry run
    itq run scripts/hist_import.py /tmp/hist_lakeshore.json --commit

Spec (JSON):
  {"vendor_pk": 11, "vendor_name": "Lakeshore Carbide",
   "source": "lakeshorecarbide.com order history (logged-in Chrome), 2026-10-04",
   "location": "SLN/Machine Shop/Unfiled - Machine Shop",
   "orders": [{"order": "63270", "date": "2024-05-20", "desc": "...",
               "subtotal": 156.77, "shipping": 12.39, "tax": 0, "total": 169.16,
               "note": "optional extra PO note",
               "lines": [{"sku": "11DRLML14", "qty": 1, "unit": 17.90,
                          "title": "seller's line title",
                          "part": 525,               # optional: attach SP to this part
                          "pack": 1,                 # optional, default 1
                          "new": {"name": ..., "category": "Tooling/Endmills",
                                  "description": ..., "keywords": ..., "link": ...},
                          "stock": "receive" | "none"   # optional, default receive
                          }]}]}

Per line, the supplier part is found by (supplier, SKU iexact). Missing -> made on
`part` if given, else a new Part from `new`, else the order is REFUSED.

Idempotent: an order whose number already exists as a PO (normalised, same as
po_check.py) is skipped whole, never topped up.

Why not InvenTree's receive_line_item(): receive_po.py's reasons, plus one of
ours -- the stock note must OPEN with [ESTIMATE] (prefix flag, TRAPS) and say
the number is a purchase document, not a count. A merged row keeps its first
line, so an existing counted row is never silently demoted: a part that
already holds stock > 0 anywhere gets its PO line marked received with NO new
stock, and is listed for review -- that stock may BE this purchase (the 08-23
Tormach receives were exactly that) and adding to it would double-count.
"""
import argparse
import datetime
import json
import os
import re
import sys
from decimal import Decimal

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.db.models import Sum  # noqa: E402

from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

TODAY = datetime.date.today()

ap = argparse.ArgumentParser()
ap.add_argument("spec")
ap.add_argument("--commit", action="store_true")
ap.add_argument("--only", default="", help="comma list of order numbers")
a = ap.parse_args()

spec = json.load(open(a.spec))
vendor = Company.objects.get(pk=spec["vendor_pk"])
assert vendor.name == spec["vendor_name"], (vendor.name, spec["vendor_name"])
dest = StockLocation.objects.get(pathstring=spec["location"])
only = {x.strip() for x in a.only.split(",") if x.strip()}


def norm(s):
    return re.sub(r"[^A-Za-z0-9]", "", s or "").lower()


po_index = {}
for po in PurchaseOrder.objects.all():
    for k in (norm(po.supplier_reference), norm(po.reference)):
        if k:
            po_index.setdefault(k, po)


def cat_by_path(path):
    hits = [c for c in PartCategory.objects.all() if c.pathstring == path]
    if len(hits) != 1:
        sys.exit(f"!! category {path!r} matches {len(hits)}")
    return hits[0]


def find_sp(ln):
    return SupplierPart.objects.filter(supplier=vendor, SKU__iexact=ln["sku"]).first()


held_before = {}
report = {"created_po": [], "skipped": [], "review": [], "new_parts": [], "refused": []}

for o in spec["orders"]:
    num = str(o["order"])
    if only and num not in only:
        continue
    hit = po_index.get(norm(num))
    print(f"\n=== {vendor.name} order {num}  {o['date']}  {o.get('desc', '')[:60]}")
    if hit:
        print(f"    SKIP: already {hit.reference} (status {hit.status})")
        report["skipped"].append(f"{num} = {hit.reference}")
        continue

    s = sum(Decimal(str(l["unit"])) * Decimal(str(l["qty"])) for l in o["lines"])
    if "subtotal" in o and abs(s - Decimal(str(o["subtotal"]))) > Decimal("0.011"):
        print(f"    REFUSE: lines sum {s} != subtotal {o['subtotal']}")
        report["refused"].append(f"{num}: lines {s} != subtotal {o['subtotal']}")
        continue

    plan, bad = [], False
    for ln in o["lines"]:
        sp = find_sp(ln)
        how = "existing sp"
        if not sp and ln.get("part"):
            how = f"NEW sp on part {ln['part']}"
        elif not sp and ln.get("new"):
            nm = ln["new"]["name"]
            if Part.objects.filter(name=nm).exists():
                print(f"    !! part named {nm!r} already exists -- give 'part' instead")
                bad = True
            how = "NEW part + sp"
        elif not sp:
            print(f"    !! no supplier part for {ln['sku']} and no part/new given")
            bad = True
            how = "MISSING"
        part = sp.part if sp else (Part.objects.get(pk=ln["part"]) if ln.get("part") else None)
        held = 0.0
        if part:
            # stock held BEFORE this run: a part received from an earlier order in
            # the same spec must not flip later orders of it into "review"
            if part.pk not in held_before:
                held_before[part.pk] = float(StockItem.objects.filter(part=part)
                                             .aggregate(q=Sum("quantity"))["q"] or 0)
            held = held_before[part.pk]
        mode = ln.get("stock", "receive")
        if mode == "receive" and held > 0:
            mode = "review"
        pack = float(ln.get("pack", sp.pack_quantity_native if sp else 1) or 1)
        plan.append((ln, sp, part, how, held, mode, pack))
        pname = part.name[:46] if part else ln.get("new", {}).get("name", "?")[:46]
        print(f"    {ln['sku']:16s} x{ln['qty']:<3} @ {float(ln['unit']):8.2f}  {how:22s} "
              f"held={held:g} -> {mode}  {pname}")
    if bad:
        report["refused"].append(f"{num}: unresolved lines")
        continue
    if not a.commit:
        continue

    # ---------------------------------------------------------------- write
    ref = PurchaseOrder.generate_reference()
    money = " ".join(f"{k} ${o[k]:.2f}" for k in ("subtotal", "shipping", "tax", "total")
                     if k in o)
    po = PurchaseOrder(
        supplier=vendor, reference=ref, supplier_reference=num,
        description=f"{vendor.name} order {num} - {o.get('desc', '')}"[:250],
        issue_date=datetime.date.fromisoformat(o["date"]),
        status=20,
        notes=(f"Historical order back-filled {TODAY} (docs/tooling-inventory.md).\n\n"
               f"SOURCE: {spec['source']}.\n\n{money}. Lines at the printed unit price."
               + (f"\n\n{o['note']}" if o.get("note") else "")
               + "\n\nStock received from this order is the PURCHASED quantity, marked "
               "[ESTIMATE] - not a count. Scott 2026-10-04: tooling has been damaged, "
               "destroyed and disposed of since; settle on a physical walk."),
    )
    po.save()
    po.refresh_from_db()
    assert po.supplier_reference == num
    po_index[norm(num)] = po
    report["created_po"].append(f"{po.reference} = {num} ({o['date']}) {money}")

    for ln, sp, part, how, held, mode, pack in plan:
        if not sp:
            if not part:
                nw = ln["new"]
                part = Part(name=nw["name"][:100], category=cat_by_path(nw["category"]),
                            description=nw.get("description", "")[:250],
                            keywords=nw.get("keywords", "")[:250], link=nw.get("link", ""),
                            IPN=nw.get("IPN", ""), component=True, purchaseable=True,
                            notes=f"Created {TODAY} from {vendor.name} order {num} "
                                  f"(historical tooling back-fill). Seller title: "
                                  f"{ln.get('title', '')}")
                part.save()
                part.refresh_from_db()
                assert part.pk
                report["new_parts"].append(f"#{part.pk} {part.name}")
            sp = SupplierPart(supplier=vendor, part=part, SKU=ln["sku"],
                              description=ln.get("title", "")[:250],
                              link=ln.get("link", "") or (ln.get("new") or {}).get("link", ""))
            sp.pack_quantity = str(int(pack)) if pack == int(pack) else str(pack)
            sp.save()
            sp.refresh_from_db()
            assert float(sp.pack_quantity_native) == pack, (sp.pk, sp.pack_quantity_native)
        unit = Decimal(str(ln["unit"]))
        li = PurchaseOrderLineItem(order=po, part=sp, quantity=ln["qty"],
                                   purchase_price=unit, purchase_price_currency="USD",
                                   notes=f"Printed: {ln.get('title', '')}"[:500])
        li.save()
        li.refresh_from_db()
        assert float(li.purchase_price.amount) == float(unit)

        pieces = float(ln["qty"]) * pack
        each = unit / Decimal(str(pack))
        if mode == "receive":
            row = StockItem.objects.filter(part=part, location=dest).first()
            stamp = (f"{vendor.name} order {num} ({o['date']}, {po.reference}): "
                     f"{pieces:g} purchased at ${each:.4f}")
            if row:
                before = float(row.quantity)
                row.quantity = before + pieces
                lead = "" if (row.notes or "").startswith("[ESTIMATE]") else "[ESTIMATE] "
                row.notes = lead + (row.notes or "") + f"\n\n+ {stamp}. {before:g} -> {before + pieces:g}."
                row.save()
                row.refresh_from_db()
                assert float(row.quantity) == before + pieces
            else:
                row = StockItem.objects.create(
                    part=part, location=dest, quantity=pieces, supplier_part=sp,
                    purchase_order=po, purchase_price=each, purchase_price_currency="USD",
                    notes=(f"[ESTIMATE] PURCHASED QUANTITY, NOT A COUNT. {stamp}. "
                           "Tooling gets broken, worn out and thrown away; Scott "
                           "2026-10-04 chose purchase-based estimates pending a "
                           "physical walk. No stocktake_date by design."))
                row.refresh_from_db()
                assert float(row.quantity) == pieces and row.notes.startswith("[ESTIMATE]")
        elif mode == "review":
            report["review"].append(
                f"{po.reference} {ln['sku']} x{ln['qty']} -> part #{part.pk} {part.name[:50]} "
                f"already holds {held:g}; no stock added")
        li.received = li.quantity
        li.save()
        li.refresh_from_db()
        assert float(li.received) == float(li.quantity)

    po.refresh_from_db()
    po.status = 30
    po.complete_date = TODAY
    po.save()
    po.refresh_from_db()
    if po.status != 30:
        PurchaseOrder.objects.filter(pk=po.pk).update(status=30, complete_date=TODAY)
        po.refresh_from_db()
    assert po.status == 30
    tot = sum(float(l.purchase_price.amount) * float(l.quantity) for l in po.lines.all())
    print(f"    WROTE {po.reference} CLOSED lines={po.lines.count()} sum={tot:.2f}")

print("\n" + "=" * 70)
for k, v in report.items():
    print(f"{k}: {len(v)}")
    for x in v:
        print(f"    {x}")
print("\n" + ("COMMITTED" if a.commit else "DRY RUN - add --commit"))
