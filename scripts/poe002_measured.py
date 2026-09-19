#!/usr/bin/env python3
"""Scott measured the 48 V pass-through. Upgrade it from inference to fact,
and retract the "no 48 V supply on site" line it falsified.

Scott, 2026-09-19: "I just uh, tested one of them out, and you're right. It,
it passes 48 volts straight through that that POE endpoint."

Two changes, and the second matters as much as the first:

1. The hazard was written as a prediction from the datasheet. It is now a
   MEASUREMENT on this hardware. Predicted and confirmed is a different claim
   from predicted, and the record should say which it is.

2. I had written "No 48 V supply on site" off an inventory sweep that returned
   nothing. Energising the base unit falsifies it -- a 48 V source exists, the
   sweep just could not see it. It was an absence-from-a-database claim
   promoted to a fact about the shop, which is the exact error the house rule
   names. Corrected in place, not deleted.

    itq run scripts/poe002_measured.py [--commit]
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

COMMIT = "--commit" in sys.argv
POE003, POE001 = 1223, 1222

OLD_48V = """**No 48 V supply on site either.** An inventory sweep for 48 V on 2026-09-19 returned nothing but this part itself; the DC bricks in this same bin are 12 V and 24 V. The base unit needs its own 48 VDC 400 mA adapter, and that adapter has no record. So the kit is missing BOTH halves of what would make it work."""

NEW_48V = """**A 48 V supply DOES exist on site, and is UNCATALOGUED.** An inventory sweep for 48 V on 2026-09-19 returned nothing but this part, and that was briefly written up here as "no 48 V supply on site." Scott then energised a base unit and measured its output, which falsifies it: something powered that unit. **The sweep's silence was a gap in the catalogue, not a fact about the shop** — an absence from the database promoted to an absence in the world, which is the error the house rule names. **Find that adapter and catalogue it**; an unrecorded 48 V brick loose in a shop full of 12 V gear is its own hazard."""

OLD_HAZ_HEAD = "**⚠ DO NOT PAIR WITH POE-002. IT WILL PUT 48 V ON A 12 V BARREL.**"
NEW_HAZ_HEAD = """**⚠ DO NOT PAIR WITH POE-002. IT PUTS 48 V ON A 12 V BARREL — MEASURED, NOT PREDICTED.**

**Confirmed on this hardware 2026-09-19.** Scott energised a base unit and metered the POE-002 barrel: *"I just uh, tested one of them out, and you're right. It, it passes 48 volts straight through that that POE endpoint."* The datasheet predicted it; the meter confirmed it. There is no step-down anywhere in this path."""

OLD_X = "**⚠ DO NOT PAIR POE-002 WITH POE-003"
NEW_X = "**⚠ DO NOT PAIR POE-002 WITH POE-003 — 48 V AT THE BARREL, MEASURED 2026-09-19"

edits = [(POE003, OLD_48V, NEW_48V), (POE003, OLD_HAZ_HEAD, NEW_HAZ_HEAD), (POE001, OLD_X, NEW_X)]

ok = True
for pk, old, new in edits:
    p = Part.objects.get(pk=pk)
    found = old in (p.notes or "")
    print(f"#{pk}  anchor {'found' if found else 'MISSING'}: {old[:52]}...")
    ok = ok and found
if not ok:
    print("\nan anchor is missing — aborting rather than writing a half edit")
    sys.exit(1)

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

for pk, old, new in edits:
    p = Part.objects.get(pk=pk)
    Part.objects.filter(pk=pk).update(notes=p.notes.replace(old, new, 1))

a = Part.objects.get(pk=POE003)
b = Part.objects.get(pk=POE001)
print("\n#1223 measurement recorded: ", "MEASURED, NOT PREDICTED" in a.notes)
print("#1223 Scott's quote present:", "passes 48 volts straight through" in a.notes)
print("#1223 48V-absence retracted:", OLD_48V not in a.notes and "UNCATALOGUED" in a.notes)
print("#1223 surplus verdict intact:", "VERDICT: SURPLUS" in a.notes)
print("#1222 cross-warning upgraded:", "MEASURED 2026-09-19" in b.notes)
