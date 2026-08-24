"""Receive PO-0020: the uxcell 15 m fiberglass sleeve, part #790.

Three separate things happen here and they are deliberately separable, because
conflating them is what produced the SHT31 ghost:

  1. BACKFILL PO-0020's issue date. It is PLACED with a null issue_date, so it
     cannot age and every aging rule skips it silently. Its own note says
     "ordered 2026-08-14". Listed in OPEN.md; this is the moment to fix it.

  2. SET units='m' on the part. First unit-bearing part in the catalogue --
     0 of 1071 today. Lowercase 'm': pint reads 'M' as molar, it passes
     validation, and the failure surfaces weeks later at the first cut.
     See docs/TRAPS.md.

  3. RECEIVE the line, then place the row where Scott says it physically is.
     A receipt records that something ARRIVED, never where it ended up. The
     location here is an OBSERVATION -- Scott carried the roll there -- which
     is the only thing that makes it different from the SHT31 claim.

Quantity is 15 m: the printed pack figure, accepted as correct because the roll
will never be measured (Scott, 2026-08-24). No stocktake_date -- not to hedge
the 15, but because that field means somebody counted, and nothing did. The
note says where the number came from so a reader in six months is not guessing.

    itq run scripts/receive_sleeve.py --location WS1
    itq run scripts/receive_sleeve.py --location WS1 --commit
"""
import argparse
import datetime
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder            # noqa: E402
from part.models import Part                      # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

PO_REF = "PO-0020"
PART_PK = 790
ORDERED = datetime.date(2026, 8, 14)      # from PO-0020's own note
QTY = 15                                  # metres, the printed pack figure
NOTE = ("15 m is the printed pack figure, accepted as correct — the roll will "
        "not be measured (Scott, 2026-08-24). NOT COUNTED: no stocktake_date, "
        "because nobody measured it. Cuts are recorded as used, so the running "
        "figure is 15 m minus what was taken; expect it good to a few cm, not "
        "a mm. If it runs dry early, the vendor's length claim was fat.")

ap = argparse.ArgumentParser()
ap.add_argument("--location", required=True,
                help="location NAME the roll physically sits in, e.g. WS1")
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

# Location names are not unique on this install and every lookup took the first
# match. Refuse an ambiguous name rather than silently picking one.
locs = list(StockLocation.objects.filter(name__iexact=a.location))
if len(locs) != 1:
    print(f"!! {a.location!r} matched {len(locs)} locations — "
          f"{[l.pathstring for l in locs]}")
    raise SystemExit(1)
loc = locs[0]

po = PurchaseOrder.objects.get(reference=PO_REF)
part = Part.objects.get(pk=PART_PK)
line = po.lines.get(part__part=part)

print(f"PO   {po.reference}  status={po.get_status_display()}  issue_date={po.issue_date}")
print(f"part #{part.pk} {part.name}")
print(f"     units={part.units!r} -> 'm'")
print(f"line #{line.pk} qty={float(line.quantity):g} received={float(line.received):g}")
print(f"dest {loc.pathstring}")
print(f"qty  {QTY} m, no stocktake_date")

if part.stock_items.exists():
    print("\n!! part already has stock rows — refusing to double-receive:")
    for s in part.stock_items.all():
        print(f"   #{s.pk} qty={float(s.quantity):g} loc={s.location}")
    raise SystemExit(1)

if not a.commit:
    print("\nDRY RUN — add --commit")
    raise SystemExit

# --- 1. issue date -------------------------------------------------------
if po.issue_date is None:
    PurchaseOrder.objects.filter(pk=po.pk).update(issue_date=ORDERED)
    got = PurchaseOrder.objects.get(pk=po.pk).issue_date
    assert got == ORDERED, f"issue_date did not stick: {got}"
    print(f"\nOK  issue_date -> {got}")
else:
    print(f"\n--  issue_date already {po.issue_date}, left alone")

# --- 2. units ------------------------------------------------------------
# .save() on this install has reported success and written nothing. Use the
# queryset, then re-read. And verify a CONVERSION, not just that it saved --
# 'M' would save perfectly and break every cut afterwards.
Part.objects.filter(pk=part.pk).update(units="m")
got = Part.objects.get(pk=part.pk).units
assert got == "m", f"units did not stick: {got!r}"
from InvenTree.conversion import convert_physical_value       # noqa: E402
probe = float(convert_physical_value("8 in", got))
assert abs(probe - 0.2032) < 1e-6, f"conversion broken: 8 in -> {probe}"
print(f"OK  units -> {got!r}   (8 in -> {probe:g} m, verified)")

# --- 3. the stock row ----------------------------------------------------
si = StockItem.objects.create(part=part, location=loc, quantity=QTY, notes=NOTE)
fresh = StockItem.objects.get(pk=si.pk)
assert float(fresh.quantity) == QTY, f"qty did not stick: {fresh.quantity}"
assert fresh.location_id == loc.pk, "location did not stick"
assert fresh.stocktake_date is None, "something stamped a stocktake date"
print(f"OK  stock #{fresh.pk}  qty={float(fresh.quantity):g} m  "
      f"loc={fresh.location.pathstring}  stocktake={fresh.stocktake_date}")

# --- 4. close the line ---------------------------------------------------
from order.models import PurchaseOrderLineItem                # noqa: E402
PurchaseOrderLineItem.objects.filter(pk=line.pk).update(received=line.quantity)
got = PurchaseOrderLineItem.objects.get(pk=line.pk).received
assert float(got) == float(line.quantity), f"received did not stick: {got}"
print(f"OK  line #{line.pk} received -> {float(got):g}")

po.refresh_from_db()
print(f"\nPO {po.reference} is now {po.get_status_display()}; "
      f"lines outstanding = {sum(1 for l in po.lines.all() if l.received < l.quantity)}")
