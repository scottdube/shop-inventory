#!/usr/bin/env python3
"""Create B-03 (Ethernet & PoE) on LW3-S1 and move the network parts into it.

Two things happening at once, and the second is the one a future session will
otherwise undo:

1. Splitting network power out of B-02. B-02 mixed 12V/24V DC bricks with PoE
   gear, and that adjacency is exactly what made today's 48 V problem possible
   -- a 48 V PoE supply sitting among 12 V barrels. B-02 keeps the bricks.

2. Scott, 2026-09-19: "I'm going to start moving stuff to these uh, laser wall
   cabinets so we can get um, those wired shells emptied out like was
   originally the plan." So B-03 living in the Laser Area while B-01 and B-02
   sit on WS2-S3 is NOT an inconsistency to tidy up -- it is the first move of
   the WS->laser-wall migration. B-01 and B-02 are expected to follow.

The B-nn id is global, not shelf-scoped, and travels with the physical bin, so
those later moves are re-parents and nothing has to be renamed or relabelled.

    itq run scripts/make_b03_ethernet.py [--commit]
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv

SHELF_PK = 511      # SLN/Laser Area/LW3/LW3-S1
B02_PK = 617
BIN_NAME = "B-03"
BIN_DESC = (
    "ETHERNET & PoE. Injectors, splitters, terminal units and their supplies. "
    "A HOME; the id travels with the bin, so a move is a re-parent. First bin "
    "of the WS2 -> laser-wall migration.")

B02_DESC = (
    "DC SUPPLIES. 12V/24V wall-warts from the 2026-09-19 salvage triage. PoE "
    "gear moved OUT to B-03 the same day: a 48V supply among 12V barrels is "
    "how something gets destroyed quietly. 6 qt clear snap-on lid. Moved "
    "WS2-S3 -> LW3-S1 on 2026-09-19.")

MOVE = [1222, 1223, 1224, 1225]

for label, txt in (("B-03 desc", BIN_DESC), ("B-02 desc", B02_DESC)):
    print(f"{label}: {len(txt)}/250")
    if len(txt) > 250:
        sys.exit(f"{label} too long")

shelf = StockLocation.objects.get(pk=SHELF_PK)
print(f"\nshelf: {shelf.pathstring}  ({shelf.stock_items.count()} items, "
      f"{shelf.get_children().count()} children)")

existing = StockLocation.objects.filter(name=BIN_NAME).first()
print(f"bin:   {'EXISTS ' + existing.pathstring if existing else 'will create under ' + shelf.pathstring}")
print("\nmoving:")
for pk in MOVE:
    p = Part.objects.get(pk=pk)
    print(f"  #{pk} {p.name[:44]:44} from {p.default_location.name if p.default_location else '-'}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

b03 = existing or StockLocation.objects.create(
    name=BIN_NAME, description=BIN_DESC, parent=shelf, structural=False)
if existing:
    StockLocation.objects.filter(pk=b03.pk).update(description=BIN_DESC, parent=shelf)
b03.refresh_from_db()

for pk in MOVE:
    Part.objects.filter(pk=pk).update(default_location=b03)
    StockItem.objects.filter(part_id=pk, location_id=B02_PK).update(location=b03)

# Scott, mid-task: "lets move B02 there as well". A re-parent, not a rename --
# the whole point of the B-nn id is that the label on the bin stays true.
StockLocation.objects.filter(pk=B02_PK).update(description=B02_DESC, parent=shelf)

b03.refresh_from_db()
b02 = StockLocation.objects.get(pk=B02_PK)
print(f"\n{b03.pathstring}   (pk {b03.pk})")
for si in StockItem.objects.filter(location=b03).order_by("part__name"):
    print(f"   [{si.pk}] #{si.part.pk} qty {si.quantity:g}  {si.part.name}")
print(f"   all four default_locations set: "
      f"{all(Part.objects.get(pk=pk).default_location_id == b03.pk for pk in MOVE)}")
print(f"\n{b02.pathstring} now holds:")
for si in StockItem.objects.filter(location=b02).order_by("part__name"):
    print(f"   [{si.pk}] #{si.part.pk} qty {si.quantity:g}  {si.part.name}")
print(f"   B-02 description updated: {'moved OUT to B-03' in b02.description}")
print(f"   B-02 re-parented:         {b02.pathstring}")
print(f"\n{shelf.pathstring} children: {[c.name for c in shelf.get_children()]}")
print(f"B-01 untouched:           {StockLocation.objects.get(name='B-01').pathstring}")
