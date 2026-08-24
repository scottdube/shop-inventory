"""Stock the 0.8mm nozzle and set minimum_stock=1 on the FR-301 consumables.

Scott, 2026-08-24: "Do we wanna set minimum stocking quantity on those to one?"

Yes, and the reason it WORKS is worth writing down, because the obvious version
of it silently does nothing. `is_part_low_on_stock` compares `get_stock_count()`
against `minimum_stock`, and that count uses `StockItem.IN_STOCK_FILTER`:

    belongs_to=None AND consumed_by=None AND customer=None
    AND is_building=False AND quantity>0 AND sales_order=None
    AND status__in=[10,50,55,85]

`belongs_to=None` is the load-bearing clause. A nozzle INSTALLED into the gun
has belongs_to set, so it stops counting as stock -- which is exactly right: it
is owned, it is findable, and it is not a spare. Minimum 1 then means "always
have one on the shelf", and it fires the moment the last spare goes onto the
gun.

Model it the other way -- nozzle sitting in the drawer record while physically
fitted to the gun -- and total stock stays 1 forever, the minimum never fires,
and you discover you have no spare when the fitted one clogs mid-job. Same
number, same field, opposite behaviour.

The 0.8mm quantity is 1 from the PURCHASE RECORD (1 purchase, 1 unit lifetime),
plus Scott saying he is filing it to the drawer. That is not a physical count,
so it gets no stocktake_date and the note says which it is.

    itq run scripts/nozzle_minimums.py
    itq run scripts/nozzle_minimums.py --commit
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part                       # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

MINIMUMS = {213: 1, 87: 1, 1084: 1}
NOTE_08 = ("Quantity 1 from the PURCHASE RECORD (Amazon: 1 purchase, 1 unit "
           "lifetime, $17.00 on 2026-07-13) plus Scott filing it to this drawer "
           "on 2026-08-24. NOT a physical count — no stocktake_date. Open the "
           "drawer and count it to promote this to a real figure.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

locs = list(StockLocation.objects.filter(name__iexact="A3-R1C2"))
assert len(locs) == 1
loc = locs[0]

p87 = Part.objects.get(pk=87)
print(f"#87 {p87.name[:52]}")
print(f"    existing stock rows: {p87.stock_items.count()}")
need_stock = not p87.stock_items.exists()
print(f"    -> {'create 1 @ ' + loc.name if need_stock else 'already stocked, leave alone'}")

print("\nminimum_stock:")
for pk, mn in MINIMUMS.items():
    p = Part.objects.get(pk=pk)
    cnt = p.get_stock_count()
    print(f"  #{pk:5} {p.name[:46]:46} stock={cnt:g} min {p.minimum_stock:g} -> {mn}"
          f"   {'LOW' if cnt < mn else 'ok'}")

if not a.commit:
    print("\nDRY RUN — add --commit")
    raise SystemExit

if need_stock:
    si = StockItem.objects.create(part=p87, location=loc, quantity=1, notes=NOTE_08)
    chk = StockItem.objects.get(pk=si.pk)
    assert float(chk.quantity) == 1 and chk.location_id == loc.pk
    assert chk.stocktake_date is None
    print(f"\nOK  stock #{chk.pk} for #87: qty=1 @ {chk.location.name}, "
          f"stocktake={chk.stocktake_date}")

for pk, mn in MINIMUMS.items():
    Part.objects.filter(pk=pk).update(minimum_stock=mn)
    got = Part.objects.get(pk=pk)
    assert float(got.minimum_stock) == mn, f"#{pk} minimum did not stick"
    print(f"OK  #{pk} minimum_stock={float(got.minimum_stock):g}  "
          f"stock={got.get_stock_count():g}  low={got.is_part_low_on_stock()}")
