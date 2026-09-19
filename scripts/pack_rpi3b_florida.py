#!/usr/bin/env python3
"""Pack the Pi 3B (#1236) into FL-01, the Florida carry box.

Scott, 2026-09-19: "actually move it to the going to FL location."

MOVED, NOT EARMARKED -- and those are two different things in this system.
florida.py's whole design is that a part bound for LRD gets a metadata
earmark and STAYS WHERE IT IS, because moving or splitting stock misstates
where things physically are and breaks counts that were correct. An FL- box
is the other state: the thing is in the box, packed, done being usable.

SO NO 'florida' METADATA KEY IS WRITTEN HERE. florida.py's _items() reads
metadata FIRST and only falls back to the FL- location test:

    if meta:                      -> reported as 'earmarked'
    elif location starts FL-      -> reported as 'packed'

Writing both would make a packed item report as merely earmarked, which is
exactly backwards. The move alone is what makes it show up correctly.

DEFAULT_LOCATION IS CLEARED, NOT SET TO FL-01. default_location is where a
spare goes HOME, never a staging area -- and RB-11 has stopped being true,
because the board is leaving the state. The LRD home is not guessed either:
the away location gets recorded on arrival, never planned.

    itq run scripts/pack_rpi3b_florida.py [--commit]
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
PART_PK = 1236
FL_PK = 504               # SLN/Florida Staging/FL-01

OLD = """**Location RB-11 is a PROPOSAL.** It holds [#395 Vilros Pi 4 kit] and [#1070 Kill A Watt] — SBCs together — but a cased Pi is bulky and nobody has looked at the space. Twice on 2026-09-19 a location correct by category turned out to be physically full."""

NEW = """**PACKED FOR FLORIDA 2026-09-19 — in `FL-01`, the carry box.** Scott: *"actually move it to the going to FL location."* Briefly filed at RB-11 with the Pi 4 kit before he redirected it.

**This is PACKED, not earmarked, and the distinction is load-bearing.** `florida.py` normally leaves a Florida-bound part exactly where it is and writes a metadata earmark, because moving stock misstates where things physically are. An `FL-` location means the opposite: it is in the box. **No `florida` metadata key is written on this row** — `florida.py` reads metadata first and falls back to the FL- location test, so carrying both would report a packed item as merely earmarked.

**`default_location` is cleared, not set to `FL-01`.** A staging area is never a home. RB-11 stopped being true the moment the board was packed, and the LRD home is not guessed — the away location is recorded on arrival, never planned.

**Take the power supply with it.** It is not on this record (see above) and a Pi 3B in Florida without a micro-USB supply is a paperweight; the undervoltage failure mode above is what a substituted phone charger buys you.

**And the SD card travels with the board**, so the Pi-hole image leaves the state too. If that configuration is wanted at SLN, image the card *before* the box goes."""

p = Part.objects.get(pk=PART_PK)
fl = StockLocation.objects.get(pk=FL_PK)
rows = StockItem.objects.filter(part=p)
print(f"#{p.pk} {p.name[:56]}")
print(f"  rows {rows.count()}: " + ", ".join(f"[{r.pk}] {r.quantity:g} @ {r.location.name}" for r in rows))
print(f"  -> [{fl.pk}] {fl.pathstring}  ({StockItem.objects.filter(location=fl).count()} rows)")
print(f"     {fl.description[:90]}")
print(f"  anchor found: {OLD in p.notes}")
print(f"  current default_location: {p.default_location.pathstring if p.default_location else 'NONE'}")
if OLD not in p.notes:
    print("\nANCHOR MISSING — refusing a half edit."); sys.exit(1)
if rows.count() != 1:
    print("\nEXPECTED EXACTLY ONE ROW."); sys.exit(1)

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

si = rows.first()
StockItem.objects.filter(pk=si.pk).update(location=fl)
Part.objects.filter(pk=p.pk).update(notes=p.notes.replace(OLD, NEW),
                                    default_location=None)
p.refresh_from_db(); si.refresh_from_db()

print(f"\n#{p.pk} {p.name}")
print(f"    stock [{si.pk}] qty {si.quantity:g} @ {si.location.pathstring}"
      f"  {'ok' if si.location_id == fl.pk else '!! WRONG'}")
print(f"    default_location  {p.default_location or 'NONE'}  <- cleared, staging is not a home")
print(f"    florida metadata  {(si.metadata or {}).get('florida', 'none')}  <- must be none")
print(f"    packed recorded   {'PACKED FOR FLORIDA 2026-09-19' in p.notes}")
print(f"    old proposal gone {OLD not in p.notes}")
print(f"    PSU reminder      {'Take the power supply with it' in p.notes}")
print(f"    card travels      {'SD card travels with the board' in p.notes}")
print(f"\nFL-01 now holds {StockItem.objects.filter(location=fl).count()} rows, "
      f"RB-11 holds {StockItem.objects.filter(location__name='RB-11').count()}")
