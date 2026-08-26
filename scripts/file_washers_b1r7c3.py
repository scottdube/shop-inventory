"""All three McMaster washer bags to B1-R7C3. They were already there.

Scott 2026-08-26: "these were in b1 r7c3 lets put all 3 there no labels needed".

  #1037 / stock 538  98687A110  M5 steel flat washer,  5.5 ID x 10 OD   100
  #1038 / stock 539  98687A111  M6 steel flat washer,  6.6 ID x 12 OD   100
  #1039 / stock 540  95610A380  M8 NYLON washer,       8.4 ID x 18 OD   100

All three on PO-0130, issued 2022-02-01.

THE CORRECTION THAT MATTERS: these were not homeless. They were in B1-R7C3 the
whole time, in a labelled cell, exactly where a person would look. What was
missing was the RECORD -- the McMaster import created stock rows with
location=NULL and nobody ever filled it in.

That reframes the 47 unlocated rows. "Owned, location unknown" has been read
all day as parts that might be lost. At least three of them were simply parts
whose location was never typed in. Those are different problems: one needs a
search, the other needs five minutes and somebody who knows the shop. The
sweep should ASK before it hunts.

The M8 is NYLON, not steel, and shares the cell with two steel ones. Recorded
on the part because "washer, M8" in a hurry is how a nylon washer ends up
somewhere it will be crushed.

No labels: Scott's call, the cell is already labelled and the bags carry
McMaster's own printed labels with the part numbers on them.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

cell = StockLocation.objects.filter(name="B1-R7C3").first()
if not cell:
    sys.exit("B1-R7C3 does not exist -- stopping rather than inventing a cell")
print(f"target: {cell.pathstring}")
print(f"  desc: {(cell.description or '(none)')[:100]}")
print(f"  currently holds: {StockItem.objects.filter(location=cell).count()} rows")

ROWS = {
    538: ("98687A110", "M5 steel flat washer"),
    539: ("98687A111", "M6 steel flat washer"),
    540: ("95610A380", "M8 NYLON washer"),
}
for pk, (sku, what) in ROWS.items():
    si = StockItem.objects.get(pk=pk)
    print(f"  [{pk}] {si.quantity:g} x {what:<22} from {si.location or 'UNLOCATED'}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

for pk, (sku, what) in ROWS.items():
    si = StockItem.objects.get(pk=pk)
    si.location = cell
    si.save()
    StockItem.objects.filter(pk=pk).update(notes=(
        f"IN B1-R7C3 ALL ALONG. Scott, 2026-08-26: the three McMaster washer "
        f"bags from PO-0130 (2022-02-01) live in this cell. Bag {sku}, sealed, "
        f"label reads 100 PCS.\n\n"
        f"THIS ROW WAS NEVER LOST. It read location=NULL since the McMaster "
        f"import, which created stock rows and never set a location. The part "
        f"was in a labelled cell the whole time. 'Owned, location unknown' "
        f"meant the RECORD did not know -- not that the shop did not.\n\n"
        f"QUANTITY 100 IS TIER-4 ACCEPTED: sealed bag, and nobody will ever "
        f"count a hundred washers. No [ESTIMATE] marker, because that marker "
        f"promises a check that will not happen. The null stocktake_date still "
        f"says correctly that nobody counted them."))
    Part.objects.filter(pk=si.part_id).update(default_location=cell)

nylon = Part.objects.get(pk=1039)
if "SHARES B1-R7C3" not in (nylon.notes or ""):
    Part.objects.filter(pk=1039).update(notes=(nylon.notes or "").rstrip() +
        "\n\nSHARES B1-R7C3 WITH TWO STEEL WASHERS, and this one is NYLON. "
        "Same cell, same nominal sizes on the label, completely different "
        "material: nylon is an insulator and a cushion, and it crushes under a "
        "load steel shrugs off. Reaching for 'a washer' in that cell without "
        "reading the bag is how a nylon one ends up under a torqued fastener.")

print("\nverify:")
for pk in ROWS:
    si = StockItem.objects.get(pk=pk)
    print(f"  [{pk}] {si.quantity:g} @ {si.location.name}  dl={si.part.default_location.name}")
print(f"\nB1-R7C3 now holds {StockItem.objects.filter(location=cell).count()} rows")
print(f"unlocated rows with stock remaining: "
      f"{StockItem.objects.filter(location__isnull=True, quantity__gt=0).count()}")
