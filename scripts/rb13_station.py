"""RB-13 holds the FX-951 soldering station, IN SERVICE.

Scott, 2026-08-25, with a photo: the station stands in RB-13 with its cord
running out of the bin, and its handpiece sits in a 599B tip cleaner on the
bench. The bin is the station's SHELF, not a kit and not free storage.

Follows the FR-301 precedent (#474 / stock #660) exactly, including the refusal
to stamp a count: "a tool being obviously singular is not the same as somebody
counting it."
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation

COMMIT = "--commit" in sys.argv
part = Part.objects.get(pk=311)
rb13 = StockLocation.objects.get(name="RB-13")

NOTE = (
    "Observed in RB-13 by Scott 2026-08-25 during the Red Bin walk, with a "
    "photograph: station standing in the bin, cord run out of it, handpiece "
    "in a 599B tip cleaner on the bench. IN SERVICE - the bin is this "
    "station's shelf, not a kit and not storage, so RB-13 is NOT a bin the "
    "walk can empty. NOT COUNTED: no stocktake_date, following the FR-301 "
    "(#474) precedent - a tool being obviously singular is not the same as "
    "somebody counting it."
)

existing = StockItem.objects.filter(part=part)
print(f"#{part.pk} {part.name}")
print(f"  existing rows: {existing.count()}")
if existing.exists():
    sys.exit("  refusing to create a second row - look first")

print(f"  would create: qty 1 @ {rb13.pathstring}, no stocktake_date")
print(f"  default_location: {part.default_location} -> None")
print("     (bare site root is the rot TRAPS.md names; there is no spare")
print("      station, so the honest value is empty, not RB-13)")

if not COMMIT:
    print("\n  DRY RUN - add --commit")
    sys.exit()

si = StockItem.objects.create(part=part, location=rb13, quantity=1, notes=NOTE)
Part.objects.filter(pk=part.pk).update(default_location=None)

si = StockItem.objects.get(pk=si.pk)
part = Part.objects.get(pk=part.pk)
ok = (si.location_id == rb13.pk and si.quantity == 1
      and si.stocktake_date is None and part.default_location is None)
print(f"\n  stock #{si.pk} qty={si.quantity:g} loc={si.location.pathstring} "
      f"stocktake={si.stocktake_date}")
print(f"  part default_location={part.default_location}")
print("  VERIFIED" if ok else "  MISMATCH - stop and look")
