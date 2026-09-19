#!/usr/bin/env python3
"""Close the pass-through crimper check on #1235. Scott has both types.

Scott, 2026-09-19: "I have both" -- an ordinary RJ-45 crimper AND a
pass-through crimper with the integrated flush cutter.

THIS WAS THE LAST OPEN TOOL QUESTION ON EITHER PART, and it is worth noting
that it survived one round of correction. When Scott said he had "multiple
punchdown tools and crimpers for this stuff", the generic claim collapsed --
but "crimpers" does not distinguish a pass-through crimper from a conventional
one, and those plugs will not finish in a conventional one. So the note kept
the specific version alive rather than closing the whole thing on the strength
of the general answer.

That was the right call and it cost one question. Collapsing it early would
have written "tools on hand, nothing to check" over a real difference.

NOTHING IS LEFT TO BUY for either #1234 or #1235. The only gap that survives
is that none of these tools are in InvenTree, which is a cataloguing job.

    itq run scripts/close_crimper_check.py [--commit]
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

COMMIT = "--commit" in sys.argv

OLD = """**So the tool requirement is specific, not generic** — and that is the part still worth checking. Scott has multiple crimpers (2026-09-19), which settles the generic question and not this one: **an ordinary RJ-45 crimper does not crimp these.** Confirm one of the crimpers on hand is a pass-through type with the integrated flush cutter before starting a run with this jar."""

NEW = """**TOOL CHECK CLOSED 2026-09-19 — the shop has a pass-through crimper.** Scott, asked specifically whether any crimper on hand was a pass-through type with the integrated flush cutter: *"I have both."* Both kinds, so these plugs can be finished properly and an ordinary crimper is available for conventional plugs.

Worth recording that this took a second question. *"Multiple crimpers"* settled the generic claim and not this one — **an ordinary RJ-45 crimper does not finish a pass-through plug**, it seats the contacts and leaves the conductors standing proud of the nose. Collapsing the specific check into the general answer would have written "tools on hand" over a real difference."""

KS_OLD = """**Whether these need a 110 punchdown tool or are the tool-less kind was NOT determined.** The bag's photograph is not a reading of the part. Open one and look before buying a tool."""

KS_NEW = """**Whether these need a 110 punchdown tool or are the tool-less kind is still NOT determined** — the bag's photograph is not a reading of the part. **It no longer gates anything**, though: Scott has multiple punchdown tools (2026-09-19), so either answer is covered and nothing needs buying. Open one and look when the time comes; it decides which tool to reach for, not whether one exists."""

EDITS = [(1235, OLD, NEW), (1234, KS_OLD, KS_NEW)]

for pk, old, _ in EDITS:
    p = Part.objects.get(pk=pk)
    hit = old in p.notes
    print(f"#{pk} {p.name[:50]:50s} anchor {'ok' if hit else 'MISS'}")
    if not hit:
        print("ANCHOR MISSING — refusing a half edit."); sys.exit(1)

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

for pk, old, new in EDITS:
    p = Part.objects.get(pk=pk)
    Part.objects.filter(pk=pk).update(notes=p.notes.replace(old, new))
    p.refresh_from_db()
    print(f"\n#{pk} {p.name}")
    print(f"    old check gone  {old not in p.notes}")
    if pk == 1235:
        print(f"    closed          {'TOOL CHECK CLOSED 2026-09-19' in p.notes}")
        print(f"    'I have both'   {'I have both' in p.notes}")
    else:
        print(f"    no longer gates {'no longer gates anything' in p.notes}")
    print(f"    no false absence {'NOTHING IN THE SHOP TERMINATES THIS.**' not in p.notes}")
