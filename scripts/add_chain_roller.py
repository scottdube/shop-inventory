"""Add the HIAORS 10mm chain roller. One, counted by Scott 2026-08-26.

Bought Amazon 2022-06-01, order 114-0413171-5281027, seller HIAORS, $8.99,
ASIN B07T62RFHJ. One item, no pack quantity stated anywhere in the listing --
and the listing was read directly rather than taken from the order-history
title, which is the mistake that had the 30203 entered as 2 instead of 5.

Listing: "Black 10mm Chain Roller Pulley Tensioner Wheel Guide ... for
Motorcycle Mini Bike Atv 125cc 140cc 160cc SSR XR125 CRF50 KLX110 Pitster Pit
Dirt Bike Parts". Description line: "10mm id Chain Roller Tensioner Guide Wheel
Chinese Dirtbike Pit Bike Motorcycle". It bolts to a swingarm to guide the
chain.

ATTRIBUTION DELIBERATELY LEFT WEAK. It was bought the SAME DAY as the R6-2RS
ten-pack, which sits in the 2022 Jet head-mover cluster, and a chain drive
plausibly wants an idler. But the thrust bearings in that same cluster turned
out to be a VISE REBUILD, so same-day is not evidence of same-job.

And there is a physical reason for doubt: this is sized for MOTORCYCLE chain
(#420/#428 class), while the head mover's drive sprocket is a nine-tooth ANSI
35 and the chain in the machine photo looks like small-pitch roller chain. A
dirt-bike chain roller may simply not fit that chain. Recorded as a question,
not an answer.
"""
import argparse, os, sys, django, datetime

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

BIN, CAT = 587, 137
NAME = "Chain Roller / Tensioner Guide Wheel, 10 mm bore (HIAORS)"
DESC = ("Black plastic chain roller with a sealed ball bearing pressed in, "
        "10 mm bore. Motorcycle / pit-bike chain guide -- bolts to a swingarm "
        "to guide or tension the drive chain.")
NOTES = (
    "BORE 10.000 mm\n\n"
    "PURCHASED: Amazon 2022-06-01, order 114-0413171-5281027, seller HIAORS, "
    "$8.99, ASIN B07T62RFHJ. One item; the listing states no pack quantity. "
    "Listing read DIRECTLY rather than from the order-history title -- that "
    "shortcut is what had the 30203 entered as 2 when it is 5.\n\n"
    "Sized for MOTORCYCLE chain (#420/#428 class), not for small-pitch roller "
    "chain.\n\n"
    "POSSIBLY BUT NOT PROBABLY the Jet head mover (#1126). Bought the same day "
    "as the R6-2RS ten-pack, which does belong to that cluster, and a chain "
    "drive plausibly wants an idler. Two reasons to hold off:\n"
    "  1. The thrust bearings in that same cluster turned out to be a VISE "
    "REBUILD. Same-day is not evidence of same-job -- a date cluster groups by "
    "WHEN and lets the reader invent the WHY.\n"
    "  2. The head mover's drive sprocket is a nine-tooth ANSI 35 and the chain "
    "in the machine photo is small-pitch. A dirt-bike roller may not fit it at "
    "all.\n"
    "Left as a question. An unattributed part is a better record than a "
    "confidently misattributed one.")

print(f"seed: 1 x {NAME}")
for p in Part.objects.filter(name__icontains="chain roller"):
    print(f"  existing: [{p.pk}] {p.name}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

binloc = StockLocation.objects.get(pk=BIN)
p = Part.objects.filter(name=NAME).first()
if not p:
    p = Part.objects.create(name=NAME, description=DESC, category_id=CAT,
                            default_location=binloc, purchaseable=True, active=True)
    print(f"part [{p.pk}] created")
Part.objects.filter(pk=p.pk).update(notes=NOTES, default_location=binloc)

si = StockItem.objects.filter(part=p, location=binloc).first()
if not si:
    si = StockItem.objects.create(part=p, location=binloc, quantity=1)
StockItem.objects.filter(pk=si.pk).update(
    stocktake_date=datetime.date(2026, 8, 26),
    notes="TALLIED 2026-08-26. Scott counted 1 in hand. Matches the order: one "
          "item, and the listing states no pack quantity.")

si.refresh_from_db()
print(f"[{p.pk}] stock[{si.pk}] qty={si.quantity:g} stocktake={si.stocktake_date}")
