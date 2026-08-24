"""Move the TCRT5000 modules from A3-R1C3 to A3-R2C7, and free R1C3 again.

A3 row 2 is already the modules row — fabricated PCBs, comms, 433MHz, small
modules, LCDs, shop-built assemblies — so R2C7 is the next slot in a row that
already means "module". R1C3 sat between the keys drawer and the FR-301
soldering consumables, where a sensor module is an orphan.

Free to do now: the drawer labels have not been printed yet, so there is
nothing physical to peel and redo. Deciding after labelling would not have been.

**Three edits, not one.** Moving stock without also moving default_location
leaves the part's home pointing at a drawer it no longer lives in, and leaving
R1C3's description in place leaves a drawer advertising contents it does not
have — which is the WS1 failure in miniature, a description written as intent.

    itq run scripts/move_tcrt_r2c7.py
    itq run scripts/move_tcrt_r2c7.py --commit
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

PART_PK, STOCK_PK = 718, 666
FROM, TO = "A3-R1C3", "A3-R2C7"

# The divider is a PHYSICAL fact reported by a person and derivable from nothing
# in the database — exactly the class CONTEXT.md says to capture on the record.
TO_DESC = ("IR REFLECTIVE / LINE SENSORS. TCRT5000-type modules, 4-pin "
           "VCC/GND/DO/AO with LM393 comparator and threshold trimpot. Reach "
           "for one when you need to know 'is something there' or 'is this "
           "stripe dark' a few millimetres away — counting slots on a wheel, "
           "finding a home position, following a line. NOT for measuring "
           "distance; the VL53L1X in B3-R4C7 is that. Kept away from the "
           "remote-control IR in B3-R4C6, which shares the word and nothing "
           "else. DIVIDED TRAY: the modules occupy ONE HALF and the other half "
           "is FREE (Scott, 2026-08-24). Filed here 2026-08-24; drawer was "
           "VERIFIED EMPTY 2026-08-23. [6 x 2-7/32 x 1-9/16 in, small]")

FROM_DESC = "VERIFIED EMPTY 2026-08-23 [6 x 2-7/32 x 1-9/16 in, small]"

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

src = StockLocation.objects.get(name=FROM)
dst = StockLocation.objects.get(name=TO)
si = StockItem.objects.get(pk=STOCK_PK)
part = Part.objects.get(pk=PART_PK)

print(f"stock #{si.pk} qty={float(si.quantity):g}")
print(f"   {si.location.pathstring}  ->  {dst.pathstring}")
print(f"part #{part.pk} home {part.default_location.name} -> {dst.name}")
print(f"{FROM} description -> back to VERIFIED EMPTY")
print(f"{TO} currently holds {dst.stock_items.count()} item(s)")

if dst.stock_items.exists():
    print(f"!! {TO} is not empty — stopping")
    raise SystemExit(1)
if si.location_id != src.pk:
    print(f"!! stock #{si.pk} is not in {FROM} — stopping")
    raise SystemExit(1)

if not a.commit:
    print("\nDRY RUN — add --commit")
    raise SystemExit

StockItem.objects.filter(pk=si.pk).update(location=dst)
assert StockItem.objects.get(pk=si.pk).location_id == dst.pk, "stock did not move"
print(f"\nOK  stock #{si.pk} -> {dst.pathstring}")

Part.objects.filter(pk=part.pk).update(default_location=dst)
assert Part.objects.get(pk=part.pk).default_location_id == dst.pk
print(f"OK  #{part.pk} home -> {dst.pathstring}")

StockLocation.objects.filter(pk=dst.pk).update(description=TO_DESC)
assert StockLocation.objects.get(pk=dst.pk).description == TO_DESC
print(f"OK  {TO} described (divider recorded)")

StockLocation.objects.filter(pk=src.pk).update(description=FROM_DESC)
assert StockLocation.objects.get(pk=src.pk).description == FROM_DESC
print(f"OK  {FROM} back to VERIFIED EMPTY — no longer advertising contents")
