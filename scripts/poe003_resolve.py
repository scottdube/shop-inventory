#!/usr/bin/env python3
"""Resolve the open question on #1223: both units are BASE units.

Scott confirmed 2026-09-19. That turns the "may not be on site" caveat into a
finding, and the finding changes the verdict: with no terminal unit the pair
cannot deliver power to anything, and completing the kit would buy a 10/100
passive version of what POE-001 (#1222) already does better off the switches
that are already installed. Recorded as SURPLUS, not disposed -- disposition
is Scott's call.

    itq run scripts/poe003_resolve.py [--commit]
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

COMMIT = "--commit" in sys.argv
PK = 1223

OLD = """**The safe partner is the kit's own terminal unit.** Whether SLN has one has NOT been established — the terminal unit is the SAME HOUSING with a different label, so "two of these" could be two base units or a base plus a terminal. **Read the labels before assuming the kit is complete.** Two base units and no terminal unit is two injectors and no way to use them."""

NEW = """**RESOLVED 2026-09-19: BOTH UNITS ARE BASE UNITS.** Scott read the labels — *"both base units."* There is **no terminal unit at SLN**. The step-down to 5 V/12 V exists nowhere on site, so as they stand these two cannot deliver usable power to anything.

**No 48 V supply on site either.** An inventory sweep for 48 V on 2026-09-19 returned nothing but this part itself; the DC bricks in this same bin are 12 V and 24 V. The base unit needs its own 48 VDC 400 mA adapter, and that adapter has no record. So the kit is missing BOTH halves of what would make it work.

**VERDICT: SURPLUS. Do not buy the missing pieces.** Completing this kit would cost a discontinued terminal unit plus a 48 V adapter, and would then deliver 5 V/12 V over a 10/100 link from a device that cannot negotiate. [POE-001 #1222] already does that job better with nothing bought at all: active 802.3af/at, gigabit, isolated, running straight off the `USW Lite 16 PoE` / `USW 24 PoE` ports that are already installed. There is no run at SLN where the DWL-P200 wins.

Kept rather than discarded because disposition is Scott's call, and the 48 V hazard below is the reason they must not be quietly repurposed in the meantime."""

p = Part.objects.get(pk=PK)
print(f"#{p.pk} {p.name}")
if OLD not in p.notes:
    print("  anchor paragraph NOT found — notes changed since; aborting rather than guessing")
    sys.exit(1)
print("  anchor found, will replace with the resolved finding")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

Part.objects.filter(pk=PK).update(notes=p.notes.replace(OLD, NEW, 1))
p.refresh_from_db()
print("\n  both-base-units recorded:", "BOTH UNITS ARE BASE UNITS" in p.notes)
print("  no-48V-supply recorded:  ", "No 48 V supply on site either" in p.notes)
print("  surplus verdict recorded:", "VERDICT: SURPLUS" in p.notes)
print("  old caveat gone:         ", OLD not in p.notes)
print("  48V hazard still present:", "48 V ON A 12 V BARREL" in p.notes)
