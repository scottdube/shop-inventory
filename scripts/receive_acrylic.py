"""Receive the acrylic sheet from PO-0138 (Amazon) into L1-D3.

Follows scripts/receive_sleeve.py: queryset .update() and re-read, never
.save() -- this install has reported success and written nothing.

Quantity defaults to the ORDERED figure. If the listing is a multipack the
ordered "1" means one pack, not one sheet, so --qty is explicit rather than
assumed. No stocktake_date unless --counted is given: receiving is not
counting.

    itq run scripts/receive_acrylic.py                 # dry run
    itq run scripts/receive_acrylic.py --commit
    itq run scripts/receive_acrylic.py --qty 6 --commit
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder, PurchaseOrderLineItem   # noqa: E402
from part.models import Part                                    # noqa: E402
from stock.models import StockItem, StockLocation               # noqa: E402

PO_REF, PART_PK, LOC = "PO-0138", 1083, "L1-D3"

ap = argparse.ArgumentParser()
ap.add_argument("--qty", type=float, default=None,
                help="sheets in hand; defaults to the ordered figure")
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

locs = list(StockLocation.objects.filter(name__iexact=LOC))
if len(locs) != 1:
    sys.exit(f"!! {LOC!r} matched {len(locs)} locations")
loc = locs[0]

po = PurchaseOrder.objects.get(reference=PO_REF)
part = Part.objects.get(pk=PART_PK)
line = po.lines.get(part__part=part)
qty = a.qty if a.qty is not None else float(line.quantity)

print(f"PO    {po.reference}  {po.get_status_display()}  issued {po.issue_date}")
for l in po.lines.all():
    mark = "<-" if l.pk == line.pk else "  "
    print(f"  {mark} line {l.pk}: {l.part.part.name[:46]:48} "
          f"{float(l.received):g}/{float(l.quantity):g}")
print(f"\npart  #{part.pk} {part.name}")
print(f"      desc: {part.description}")
print(f"      units={part.units!r}  default_location="
      f"{part.default_location.pathstring if part.default_location else '(none)'}")
sp = line.part
print(f"      supplier part: {sp.SKU}  pack={sp.pack_quantity!r}")
print(f"\ndest  {loc.pathstring}")
print(f"qty   {qty:g} sheets  (ordered {float(line.quantity):g} pack)  COUNTED at receipt")

if part.stock_items.exists():
    print("\n!! part already has stock rows — refusing to double-receive:")
    for s in part.stock_items.all():
        print(f"   #{s.pk} qty={float(s.quantity):g} loc={s.location}")
    raise SystemExit(1)

if not a.commit:
    print("\nDRY RUN — add --commit")
    raise SystemExit

NOTE = (f"Received from {PO_REF} (Amazon) 2026-08-24 into {LOC}. {qty:g} SHEETS "
        f"counted out of the box by Scott on receipt — the order line reads 1, "
        f"which is one 4-pack, so quantity here is sheets and not packs. "
        f"COUNTED at receipt, hence the stocktake_date. Cast vs extruded is "
        f"still unverified: the listing says cast but that is seller copy, and "
        f"it matters for laser cutting.")

import datetime                                                # noqa: E402
TODAY = datetime.date(2026, 8, 24)
si = StockItem.objects.create(part=part, location=loc, quantity=qty, notes=NOTE)
# A count is a count: Scott tallied the box on receipt, so it gets a date.
StockItem.objects.filter(pk=si.pk).update(stocktake_date=TODAY)
fresh = StockItem.objects.get(pk=si.pk)
assert float(fresh.quantity) == qty, f"qty did not stick: {fresh.quantity}"
assert fresh.location_id == loc.pk, "location did not stick"
assert fresh.stocktake_date == TODAY, f"stocktake did not stick: {fresh.stocktake_date}"
print(f"\nOK  stock #{fresh.pk}  qty={float(fresh.quantity):g}  "
      f"loc={fresh.location.pathstring}")

if part.default_location_id is None:
    Part.objects.filter(pk=part.pk).update(default_location=loc)
    got = Part.objects.get(pk=part.pk).default_location
    assert got and got.pk == loc.pk, "default_location did not stick"
    print(f"OK  default_location -> {got.pathstring}")
else:
    print(f"--  default_location already {part.default_location.pathstring}")

if str(sp.pack_quantity).strip() in ("1", "", "None"):
    type(sp).objects.filter(pk=sp.pk).update(pack_quantity="4")
    got = type(sp).objects.get(pk=sp.pk).pack_quantity
    assert str(got) == "4", f"pack_quantity did not stick: {got!r}"
    print(f"OK  supplier pack_quantity 1 -> {got}   (SKU is a 4-pack)")

PurchaseOrderLineItem.objects.filter(pk=line.pk).update(received=line.quantity)
got = PurchaseOrderLineItem.objects.get(pk=line.pk).received
assert float(got) == float(line.quantity), f"received did not stick: {got}"
print(f"OK  line #{line.pk} received -> {float(got):g}")

po.refresh_from_db()
out = sum(1 for l in po.lines.all() if l.received < l.quantity)
print(f"\nPO {po.reference} {po.get_status_display()}; lines outstanding = {out}")
if out == 0:
    print("    fully received — still PLACED, so it will keep aging. Close it.")
