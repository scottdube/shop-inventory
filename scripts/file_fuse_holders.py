#!/usr/bin/env python3
"""File 8 inline fuse holders to L2-D2 and close the bundle question.

Scott, 2026-09-15: count "8 in the bag"; and on whether #1143's 150-piece
fuse kit is the other half of this same ASIN, "who knows old stock."

THAT IS AN ANSWER, AND IT IS RECORDED AS ONE. Not "unresolved, ask later" --
the person who would know has said he does not. Writing it down as closed is
the difference between a question that dies and a question that gets re-asked
by every future reader who notices two fuse records and one bundle label.

So the two parts stay UNLINKED and this ASIN stays on the holders only. The
alternative -- merging on a hunch -- would attach a real purchase record to
#1143, whose entire provenance is a photograph of a drawer taken 2026-08-28.
An unprovable link is worse than an honest gap, because it looks like
evidence.

8 of a 10-pack. The missing two are not explained and nothing here pretends
otherwise; "old stock" covers the shortfall as well as the bundle.

    itq run scripts/file_fuse_holders.py
    itq run scripts/file_fuse_holders.py --commit
"""
import os
import sys
from decimal import Decimal

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
COUNT = Decimal("8")

p = Part.objects.get(pk=1203)
loc = StockLocation.objects.filter(name="L2-D2").first()
assert loc, "L2-D2 not found"

OPEN_Q_START = "**OPEN, 2026-09-14:**"
RESOLVED = """**CLOSED 2026-09-15 — UNKNOWABLE, not unresolved.** Asked whether #1143 (the 150-piece 5 x 20 glass fuse kit in L2-D2) is the other half of this bundle, Scott said: *"who knows old stock."*

So the two parts stay UNLINKED and this ASIN stays on the holders alone. The person who would know has said he does not, and that is a finding rather than a gap to revisit — a future reader who spots two fuse records and one bundle label should read this and stop, not re-open it.

Merging them was the tempting move and would have been wrong: #1143's entire provenance is a photograph of drawer L2-D2 taken 2026-08-28. Attaching a real ASIN and purchase to it would have dressed a guess as evidence. The original reasoning, kept:"""

print(f"[{p.pk}] {p.name}")
print(f"  dest  {loc.pathstring}")
print(f"  count {float(COUNT):g} (of a 10-pack)")
print(f"  open-question anchor present: {OPEN_Q_START in (p.notes or '')}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

assert OPEN_Q_START in p.notes, "anchor missing — refusing to guess"
Part.objects.filter(pk=1203).update(
    notes=p.notes.replace(OPEN_Q_START, RESOLVED + "\n\n> " + OPEN_Q_START, 1))

si = StockItem.objects.create(
    part=p, location=loc, quantity=COUNT,
    notes=("COUNTED 8 by Scott 2026-09-15 during the wire-shelf stock-in. "
           "Tallied, not an estimate.\n\n"
           "EIGHT OF A TEN-PACK. The two missing are not accounted for; Scott "
           "on the whole purchase: \"who knows old stock.\" Recorded as "
           "unexplained rather than assumed consumed.\n\n"
           "Filed with the 5 x 20 glass fuses (#1143) they take, so holder and "
           "fuse are reached for together."),
)

p.default_location = loc
p.save()
p.refresh_from_db()
if p.default_location_id != loc.pk:
    Part.objects.filter(pk=1203).update(default_location=loc)
    p.refresh_from_db()

print(f"\nstock {si.pk}: {float(si.quantity):g} @ {si.location.pathstring}")
print(f"home: {p.default_location.pathstring}")
print(f"bundle question closed: {'CLOSED 2026-09-15' in p.notes}")
