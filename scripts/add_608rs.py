"""Add the 608RS ball bearings: 49, counted by Scott 2026-08-26.

The first genuinely RADIAL bearing in the bin, and the one that made
"Bearings & Motion" the right name over "Linear Motion".

49 is a TALLIED count with a stocktake_date -- Scott counted them in hand. Note
that 49 is not a pack number, which is itself evidence the count is real: packs
come in 10s, 20s and 100s.
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
NAME = "Ball Bearing 608RS, 8 x 22 x 7 mm"
DESC = ("Deep-groove radial ball bearing, 608 series -- 8 mm bore, 22 mm OD, "
        "7 mm wide, rubber sealed. The commodity skate-bearing size.")
NOTES = (
    "8 mm bore, same shaft size as the LM8UU bushings in this bin. They are NOT "
    "interchangeable: the 608 is a RADIAL bearing that spins on a shaft, the "
    "LM8UU is a LINEAR bushing that slides along one. Sharing a bore diameter "
    "is the trap, not the feature.\n\n"
    "SEAL COUNT NOT CONFIRMED: '608RS' is one rubber seal, '608-2RS' is two. "
    "Scott's reading was 608RS. Worth a look before specifying one for anything "
    "that has to keep grit out from both sides.\n\n"
    "No purchase order in this system matches these; vendor and date unknown, "
    "so none is claimed.")
STOCK_NOTE = (
    "TALLIED 2026-08-26. Scott counted 49 in hand.\n\n"
    "49 is not a pack number -- packs come in 10s, 20s and 100s -- which is "
    "itself a small piece of evidence that this is a real count of an "
    "already-used-from supply rather than a figure read off a bag.")

print(f"duplicate guard:")
for p in Part.objects.filter(name__icontains="608"):
    print(f"  [{p.pk}] {p.name}")
binloc = StockLocation.objects.get(pk=BIN)
print(f"bin: {binloc.pathstring}\nseed: 49 x {NAME}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

p = Part.objects.filter(name=NAME).first()
if not p:
    p = Part.objects.create(name=NAME, description=DESC, category_id=CAT,
                            default_location=binloc, purchaseable=True, active=True)
    print(f"part [{p.pk}]")
Part.objects.filter(pk=p.pk).update(notes=NOTES, default_location=binloc)

si = StockItem.objects.filter(part=p, location=binloc).first()
if not si:
    si = StockItem.objects.create(part=p, location=binloc, quantity=49)
StockItem.objects.filter(pk=si.pk).update(
    notes=STOCK_NOTE, stocktake_date=datetime.date(2026, 8, 26))

si.refresh_from_db(); p.refresh_from_db()
print(f"\n[{p.pk}] stock[{si.pk}] qty={si.quantity:g} "
      f"stocktake={si.stocktake_date} @ {si.location.name}")
