#!/usr/bin/env python3
"""Move the DC pigtails from B0-R1C4 to B0-R1C3.

Scott, 2026-09-14: "R1c4 had a din cable not enough room, move next door to
c3." A volume problem -- C4 already holds the 5-pin DIN cable and 24 pigtails
do not fit alongside it.

C3 WAS SCOPED FOR VIDEO CABLES AND HAD NEVER BEEN USED. Its description
reserved it for VGA, DisplayPort, DVI and FFC/FPC ribbons -- written as intent
on 2026-08-29, with nothing ever filed into it. So this is not a collision
with real contents; it is a plan being overtaken by an actual need, which is
the right way round.

The re-scope is recorded honestly: C3 becomes DC POWER, the video-cable
intention is noted as displaced rather than silently deleted, and B0-R2C2 is
named as where video should go instead. Deleting the old scope without saying
where its contents were meant to live is how a wall loses its organising
principle one drawer at a time.

    itq run scripts/pigtails_to_r1c3.py
    itq run scripts/pigtails_to_r1c3.py --commit
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
ROWS = [802, 803]           # female jack, male plug
DEST = 564                  # B0-R1C3

dest = StockLocation.objects.get(pk=DEST)
print(f"destination: {dest.pathstring}")
print(f"currently holds: {StockItem.objects.filter(location=dest).count()} row(s)\n")

for pk in ROWS:
    si = StockItem.objects.get(pk=pk)
    print(f"  {si.part.name[:60]}")
    print(f"     {si.location.pathstring} -> {dest.pathstring}   qty {float(si.quantity):g}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

for pk in ROWS:
    si = StockItem.objects.get(pk=pk)
    si.location = dest
    si.save()
    si.refresh_from_db()
    if si.location_id != DEST:
        StockItem.objects.filter(pk=pk).update(location=dest)
        si.refresh_from_db()
    assert si.location_id == DEST, f"row {pk} did not move"

    p = si.part
    p.default_location = dest
    p.save()
    p.refresh_from_db()
    if p.default_location_id != DEST:
        Part.objects.filter(pk=p.pk).update(default_location=dest)
        p.refresh_from_db()
    print(f"  ✓ row {pk} and part #{p.pk} home -> {dest.pathstring}")

dest.description = (
    "DC POWER PIGTAILS & LEADS. Barrel jacks and plugs on flying leads, DC "
    "power tails, and the short leads that get a supply into a project. "
    "Currently the 5.5 x 2.1 mm male and female pigtails.\n\n"
    "RE-SCOPED 2026-09-14, from video cables. This drawer had been reserved on "
    "2026-08-29 for VGA / DisplayPort / DVI and FFC-FPC ribbons and NOTHING WAS "
    "EVER FILED IN IT -- a plan, not contents. Scott needed the volume: "
    "\"R1c4 had a din cable not enough room, move next door to c3.\"\n\n"
    "SO VIDEO & DISPLAY CABLES NOW HAVE NO DRAWER. B0-R2C2 is free and large "
    "and is the obvious home when the first one turns up. Recorded here rather "
    "than dropped, so the wall does not quietly lose a category nobody notices "
    "is missing until they are holding a VGA lead.\n\n"
    "NOT mains cordage. IEC and extension cords are C4 if small, WS1-S5 if "
    "bulky. The split is DC-to-a-project versus AC-to-an-outlet. "
    "[6 x 4-9/16 x 2-3/16 in, large]"
)
dest.save()
dest.refresh_from_db()
print(f"\nC3 re-scoped: {'DC POWER PIGTAILS' in dest.description}")
print(f"video displacement recorded: {'B0-R2C2' in dest.description}")

c4 = StockLocation.objects.get(pk=565)
print(f"\nC4 now holds {StockItem.objects.filter(location=c4).count()} row(s):")
for si in StockItem.objects.filter(location=c4):
    print(f"   {si.part.name[:60]}  qty={float(si.quantity):g}")
print(f"C3 now holds {StockItem.objects.filter(location=dest).count()} row(s)")
