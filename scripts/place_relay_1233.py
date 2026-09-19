#!/usr/bin/env python3
"""Give relay #1233 a home: A3-R6C5, and record why B3-R6C4 could not take it.

THE OBVIOUS ANSWER WAS B3-R6C4, THE RELAY DRAWER. Scott, at the drawer
2026-09-19: "no room in that drawer". It holds six parts already. And B3 has
NO empty small drawer anywhere -- rows 1-4 are the small ones and all 32 are
occupied -- so staying on the same wall was not an option either.

WHY A3-R6C5. Scott: "small drawer is adequate" -- an ISO mini relay is about
an inch cubed plus bracket and pigtail, well inside a small drawer's
6 x 2-7/32 x 1-9/16 in. A3 is the all-small electronics cabinet, and ROW 6 IS
ALREADY THE RELAY ROW: A3-R6C7 holds the Shelly Plus 2PM and A3-R6C8 the
MHCOZY 2-channel. C4 and C5 are both verified empty; C5 is the nearer of the
two to that pair.

NOT B1 OR B2, which have empty small drawers going spare. They are the metric
and imperial FASTENER cabinets. A few electronics have already drifted into B2
(steppers, motors) and that is drift, not a precedent to extend.

NOT LW3-S2 BESIDE DP-001 either. The relay is free stock, and
`default_location` is where a SPARE goes home -- never a project bin. Filing
it with the panel would make it look committed to a build that has not
started, and hide it from the next "do we own a 40 A relay?".

AND THIS RETRACTS WHAT #1233's NOTES SAY. They claim a pigtailed relay with a
bracket is "a different shape from the board modules in B3-R6C4" and so must
not be assumed to fit. Wrong on the facts -- B3-R6C4 already holds #33, an
MY2NJ power relay WITH ITS SOCKET, a discrete lump rather than a board. The
drawer was never board-only. Declining to guess was right; the reason given
for declining was invented, and the query that would have settled it took ten
seconds. It turned out not to fit for a reason I never considered: it is full.

    itq run scripts/place_relay_1233.py [--commit]
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
PART_PK = 1233
LOC_PK = 183              # SLN/Bin Wall/A3/A3-R6C5
FULL_PK = 333             # SLN/Bin Wall/B3/B3-R6C4 — full, per Scott
QTY = 1                   # stated by Scott 2026-09-19, one unit

LOC_DESC = ("AUTOMOTIVE / 12 V POWER RELAYS. ISO mini relays on brackets with "
            "pigtails - tens of amps of 12 VDC, unlike the board modules in "
            "B3-R6C4 and the smart relays at C7/C8 on this row. Opened "
            "2026-09-19: B3-R6C4 is FULL. [6 x 2-7/32 x 1-9/16 in, small]")

OLD = """**Quantity is one, stated by Scott. Location not set — it comes from Scott.** A pigtailed relay with a bracket is a different shape from the board modules in `B3-R6C4`, and assuming it fits that drawer would put a guess in the record that nothing would ever re-ask."""

NEW = """**Quantity is one, stated by Scott 2026-09-19. Filed in `A3-R6C5`.**

**The relay drawer `B3-R6C4` could not take it — Scott, at the drawer: *"no room in that drawer"*.** It already holds six parts. And B3 has **no empty small drawer anywhere** (rows 1–4 are the small ones; all 32 are occupied), so staying on that wall was not an option either. A3 is the all-small electronics cabinet and **row 6 is already the relay row** — `A3-R6C7` Shelly Plus 2PM, `A3-R6C8` MHCOZY 2-channel — so the relay is with its own kind, two drawers along.

Scott, 2026-09-19: *"small drawer is adequate"*. An ISO mini relay is roughly an inch cubed plus bracket and pigtail, well inside 6 × 2-7/32 × 1-9/16 in.

**Deliberately NOT on `LW3-S2` beside [DP-001 #1232]**, even though that is the build it is destined for. `default_location` is where a spare goes home, never a project bin; filing it with the panel would make it look committed to a build that has not started.

**Correction, 2026-09-19.** This note previously said a pigtailed bracket relay was "a different shape from the board modules in B3-R6C4" and that assuming it fit would be a guess. The caution was right and the fact behind it was wrong — B3-R6C4 already holds [#33 MY2NJ Power Relay DPDT + socket], a discrete lump rather than a board. Declining to guess is correct; writing the reason for declining as though it were established is not. It did turn out not to fit, for a reason I never considered: the drawer is full."""

FULL_NOTE = (" FULL as of 2026-09-19 (Scott, at the drawer) — six parts in it; "
             "new automotive/12 V power relays go to A3-R6C5.")

p = Part.objects.get(pk=PART_PK)
loc = StockLocation.objects.get(pk=LOC_PK)
full = StockLocation.objects.get(pk=FULL_PK)
print(f"#{p.pk} {p.name}")
print(f"  -> [{loc.pk}] {loc.pathstring}")
print(f"     was: {loc.description!r}")
print(f"     rows currently in it: {StockItem.objects.filter(location=loc).count()}")
print(f"  existing stock rows for this part: {StockItem.objects.filter(part=p).count()}")
print(f"  anchor found in notes: {OLD in p.notes}")
print(f"  LOC_DESC {len(LOC_DESC)}/250")
if OLD not in p.notes:
    print("\nANCHOR NOT FOUND — refusing a half edit.")
    sys.exit(1)
if len(LOC_DESC) > 250:
    print("\nLOCATION DESCRIPTION TOO LONG.")
    sys.exit(1)
if StockItem.objects.filter(location=loc).exists():
    print("\nA3-R6C5 IS NOT EMPTY ANY MORE — stop and re-survey.")
    sys.exit(1)

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

StockLocation.objects.filter(pk=loc.pk).update(description=LOC_DESC)
if FULL_NOTE.strip() not in (full.description or ""):
    StockLocation.objects.filter(pk=full.pk).update(
        description=(full.description or "") + FULL_NOTE)
Part.objects.filter(pk=p.pk).update(notes=p.notes.replace(OLD, NEW),
                                    default_location=loc)
si = StockItem.objects.filter(part=p, location=loc).first()
if si is None:
    si = StockItem.objects.create(part=p, location=loc, quantity=QTY)

p.refresh_from_db(); loc.refresh_from_db(); full.refresh_from_db(); si.refresh_from_db()
print(f"\n#{p.pk} {p.name}")
print(f"    default_location   {p.default_location.pathstring}")
print(f"    stock [{si.pk}] qty {si.quantity:g} @ {si.location.pathstring}"
      f"  {'ok' if float(si.quantity) == QTY else '!! WRONG'}")
print(f"    old claim gone     {OLD not in p.notes}")
print(f"    correction filed   {'Correction, 2026-09-19' in p.notes}")
print(f"    B3-full recorded   {'no room in that drawer' in p.notes}")
print(f"    not-a-project-bin  {'NOT on `LW3-S2`' in p.notes}")
print(f"\n    A3-R6C5 desc  {loc.description[:90]}...")
print(f"    B3-R6C4 desc  ...{full.description[-96:]}")
print(f"\n    label: NOT printed — A3-R6C5 needs a new tape, ask Scott first")
