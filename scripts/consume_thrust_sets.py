"""Zero the two thrust-bearing sets: used on repair projects, years ago.

Scott 2026-08-26, on the four unlocated rows: "used on repair projects."

The purchase record agrees and explains why they were never findable. Two
McMaster orders, each a MATCHED SET bought for one job:

  PO-0126, issued 2022-08-01 -- 5909K25 bearing + 2x 5909K251 washers  (3/8")
  PO-0125, issued 2022-10-04 -- 5909K35 bearing + 2x 5909K48  washers  (7/8")

Four years old, single quantities, bought as complete sets. That is a repair,
not stock. They were not lost; they were fitted.

Zeroed rather than deleted, following stock 341's precedent: a zero with an
explanation is a fact, a zero without one is a question that costs somebody a
trip to the bench.

`delete_on_deplete` MUST be cleared first. The first run of this script called
take_stock() straight down to zero and InvenTree DELETED the row -- destroying
the very explanation the zero exists to carry. Row 522 was lost that way and is
recreated here.
"""
import argparse, os, sys, django, datetime

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part
from stock.models import StockItem

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()

# part_pk -> (po, issued, which set)
SETS = {
    1021: ("PO-0126", "2022-08-01", '3/8" set'),
    1022: ("PO-0126", "2022-08-01", '3/8" set'),
    1018: ("PO-0125", "2022-10-04", '7/8" set'),
    1019: ("PO-0125", "2022-10-04", '7/8" set'),
}

def note(po, when, which, recreated):
    t = (f"COUNTED 0 — correct, and not an error. Scott, 2026-08-26: used on "
         f"repair projects.\n\n"
         f"Bought on {po}, issued {when}, as part of the {which}: the bearing and "
         f"its washers came on one order in single quantities. That is a repair, "
         f"not stock. These rows were never lost — they were fitted, four years "
         f"ago.\n\n"
         f"The row exists AT ZERO so the next person who wants a thrust bearing "
         f"finds the McMaster part number instead of starting from nothing. "
         f"default_location still points at Bearings & Motion; that is where one "
         f"would go if bought again.")
    if recreated:
        t += ("\n\nThis row was RECREATED 2026-08-26. The original (stock 522) was "
              "deleted by InvenTree when take_stock() took it to zero with "
              "delete_on_deplete still set — the depletion hook removed the row "
              "and the explanation with it. Quantity and provenance are carried "
              "over from that row; the tracking history is not.")
    return t

for ppk, (po, when, which) in SETS.items():
    rows = StockItem.objects.filter(part_id=ppk)
    print(f"part {ppk}: {rows.count()} rows {[(r.pk, float(r.quantity)) for r in rows]}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

for ppk, (po, when, which) in SETS.items():
    si = StockItem.objects.filter(part_id=ppk).first()
    recreated = False
    if not si:
        # delete_on_deplete cleared AT CREATION, so a zero row can exist at all.
        si = StockItem.objects.create(part_id=ppk, quantity=0, location=None,
                                      delete_on_deplete=False)
        recreated = True
        print(f"  part {ppk}: recreated stock [{si.pk}] at 0")
    else:
        StockItem.objects.filter(pk=si.pk).update(delete_on_deplete=False)
        si.refresh_from_db()
        if si.quantity > 0:
            si.take_stock(si.quantity, user,
                          notes="Consumed on a repair project. Scott, 2026-08-26.")
        survived = StockItem.objects.filter(pk=si.pk).exists()
        print(f"  part {ppk}: stock [{si.pk}] -> 0, row survived: {survived}")
        if not survived:
            sys.exit(f"row {si.pk} was deleted anyway — stop and investigate")
    StockItem.objects.filter(pk=si.pk).update(
        stocktake_date=datetime.date(2026, 8, 26),
        notes=note(po, when, which, recreated))

print("\nverify:")
for ppk in SETS:
    p = Part.objects.get(ppk_ := ppk) if False else Part.objects.get(pk=ppk)
    rows = StockItem.objects.filter(part_id=ppk)
    for si in rows:
        print(f"  part {ppk} stock[{si.pk}] qty={si.quantity:g} "
              f"depl={si.delete_on_deplete} stocktake={si.stocktake_date} "
              f"dl={p.default_location.name if p.default_location else 'NONE'}")
    if not rows:
        print(f"  part {ppk}: NO ROW — failed")
