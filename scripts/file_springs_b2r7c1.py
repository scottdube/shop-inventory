"""File the springs into B2-R7C1. Scott: "theyre all there".

Scott 2026-08-26: "they're all there that we talked about this afternoon".

That is a person looking at the cell, which is the thing that has been missing
all day -- every one of these rows stayed unlocated on purpose because nobody
had confirmed the shelf.

FILED, and the five are NOT in the same state:

  COUNTED and located -- handled on the bench this afternoon:
    #976   6  compression, 3 in x 0.5 in OD      (W.B. Jones, via McMaster)
    #978   2  extension, HOOK ends, 5 in         (Associated Spring Raymond)
    #1132  3  extension, LOOP ends, 4-1/2 in     (P-9602 retail card + 1 loose)

  LOCATED but NOT counted -- never came out on the bench:
    #1001  5  302 stainless compression, 1 in
    #1002 12  compression, 0.938 in x 0.188 in OD

The second pair get a location and NO stocktake_date. Scott confirmed they are
in the cell; he did not count them, and their quantities are still PO-0122's
line figures from 2023 -- what was bought, not what is left. Location is a fact
he observed; quantity is not, and conflating the two is how the SHT31 rows went
wrong in the other direction.

#977 IS DELIBERATELY EXCLUDED. It is at zero, fitted to the sim rudder pedals.
"All there" cannot include it, and sweeping it in with the others would undo an
hour-old correction.
"""
import argparse, os, sys, time, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.utils import OperationalError
from part.models import Part
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

def retry(fn, what, tries=6):
    for i in range(tries):
        try:
            return fn()
        except OperationalError as e:
            if "locked" not in str(e).lower() or i == tries - 1:
                raise
            print(f"  locked on {what}, retry {i+1}")
            time.sleep(0.5 * (2 ** i))

cell = StockLocation.objects.get(pk=289)   # B2-R7C1
COUNTED = [976, 978, 1132]
UNCOUNTED = [1001, 1002]

print(f"target: {cell.pathstring}")
for pk in COUNTED + UNCOUNTED:
    si = StockItem.objects.filter(part_id=pk).first()
    tag = "counted" if pk in COUNTED else "NOT counted"
    print(f"  [{pk}] {si.quantity:>4g}  {tag:<12} {si.part.name[:46]}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

for pk in COUNTED + UNCOUNTED:
    si = StockItem.objects.filter(part_id=pk).first()
    def move(si=si):
        si.location = cell
        si.save()
    retry(move, f"locate {pk}")

for pk in UNCOUNTED:
    si = StockItem.objects.filter(part_id=pk).first()
    retry(lambda si=si: StockItem.objects.filter(pk=si.pk).update(
        notes=(si.notes or "").rstrip() +
        "\n\nLOCATED 2026-08-26 to B2-R7C1, the springs cell. Scott: \"they're "
        "all there that we talked about this afternoon.\"\n\n"
        "**LOCATED, NOT COUNTED — and the stocktake_date is still null on "
        "purpose.** Scott confirmed this is IN the cell; he did not count it. "
        "The quantity is still PO-0122's line figure from 2023-01-09 — what was "
        "BOUGHT, not what is left. Every spring that has been counted today came "
        "back different from its purchase figure or needed the date set by hand.\n\n"
        "Location is a fact somebody observed. Quantity here is not. Treating "
        "the two as one claim is how these rows went wrong in the first place."),
        f"note {pk}")

print("\nverify:")
for pk in COUNTED + UNCOUNTED:
    si = StockItem.objects.filter(part_id=pk).first()
    print(f"  [{pk}] {si.quantity:>4g} @ {si.location.name}  stocktake={si.stocktake_date}")
z = StockItem.objects.filter(part_id=977).first()
print(f"  [977] {z.quantity:g} @ {z.location or 'UNLOCATED'}  <- excluded, consumed on BO-0015")
print(f"\ncell holds {StockItem.objects.filter(location=cell).count()} rows")
print(f"unlocated rows with stock: "
      f"{StockItem.objects.filter(location__isnull=True, quantity__gt=0).count()}")
