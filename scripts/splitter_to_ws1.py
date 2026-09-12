#!/usr/bin/env python3
"""Move the power cord splitters out of B0-R1C4 onto WS1-S5.

Scott, 2026-09-12: "cord splitter wont fit in those bins needs to go on wire
shelves, ws1 second to bottom currently has power cords."

A fit failure, not a filing error. B0-R1C4 is the POWER & MISC CABLES drawer
and a mains splitter is exactly what its description describes -- the drawer
is simply 6 x 4-9/16 x 2-3/16 in and the thing does not go in. That distinction
matters for the next person, so B0-R1C4's description now carries the size
limit rather than being quietly narrowed in scope.

Second from the bottom is S5: S1 is the TOP shelf and S6 the bottom, a
convention set 2026-08-22.

The BO-0006 allocation is untouched by this. BuildItem points at the stock
item, not at its location, so the splitter can move shelves while staying
committed to the sim.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

si = StockItem.objects.get(pk=799)
ws1s5 = StockLocation.objects.get(pk=450)
old = si.location

print(f"{si.part.name[:56]}  qty={float(si.quantity):g}")
print(f"  {old.pathstring}  ->  {ws1s5.pathstring}")

si.location = ws1s5
si.save()
si.refresh_from_db()
if si.location_id != ws1s5.pk:
    StockItem.objects.filter(pk=si.pk).update(location=ws1s5)
    si.refresh_from_db()
assert si.location_id == ws1s5.pk, "move did not persist"

p = Part.objects.get(pk=1180)
p.default_location = ws1s5
p.save()
p.refresh_from_db()
if p.default_location_id != ws1s5.pk:
    Part.objects.filter(pk=1180).update(default_location=ws1s5)
    p.refresh_from_db()
print(f"  default_location -> {p.default_location.pathstring}")

# Record what Scott just said about the shelf. Contents STATED, not counted.
ws1s5.description = (
    "WS1-S5 — shelf 5 of 6, counting down from the top; SECOND FROM THE "
    "BOTTOM. S1 is the top shelf, S6 the bottom (convention set 2026-08-22).\n\n"
    "POWER CORDS live here. Scott, 2026-09-12: \"ws1 second to bottom "
    "currently has power cords.\" That is his statement about the shelf, not "
    "a count -- most of what is on it has never been catalogued, which is "
    "true of all of WS1. The mains splitters (#1180) are the first thing "
    "recorded against it.\n\n"
    "THIS IS WHERE BULKY MAINS CORDAGE GOES. The bin wall's power drawer "
    "(B0-R1C4) is the right CATEGORY and the wrong SIZE -- see its "
    "description. Anything that coils bigger than a fist belongs here."
)
ws1s5.save()
ws1s5.refresh_from_db()
assert "power cords" in ws1s5.description.lower()

b0r1c4 = StockLocation.objects.get(pk=565)
add = (
    "\n\nSIZE LIMIT, learned 2026-09-12: the drawer is 6 x 4-9/16 x 2-3/16 in "
    "and will not take bulky mains cordage. The NEMA 5-15 splitters (#1180) "
    "were filed here on receipt because the category fits, and they do not "
    "physically go in. They live on WS1-S5 with the rest of the power cords. "
    "This drawer is for light, flexible leads -- DC barrel, audio, short IEC. "
    "The category is right; check the coil against the drawer before filing."
)
if "SIZE LIMIT" not in (b0r1c4.description or ""):
    b0r1c4.description = (b0r1c4.description or "") + add
    b0r1c4.save()
    b0r1c4.refresh_from_db()
print(f"  B0-R1C4 note added: {'SIZE LIMIT' in b0r1c4.description}")

# allocation must survive the move
si.refresh_from_db()
print(f"\n  stock {si.pk}: qty={float(si.quantity):g}  "
      f"free={float(si.unallocated_quantity()):g}  @ {si.location.pathstring}")
