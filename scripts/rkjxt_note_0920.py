#!/usr/bin/env python3
"""Rewrite row #9's location note: the 2026-08-27 either/or is now answered.

The note asked a real question -- "in the mobile cart, or already fitted into
the G1000 panel?" -- and said it does not get resolved by picking the likelier
option. Today's MC-T3 count answered it, and the answer was BOTH: one in the
cart, one fitted. Leaving the question standing next to its own answer is the
"stale explanation" trap in docs/TRAPS.md, which says the reason has to be
rewritten in the SAME pass as the thing that resolved it.

    itq run scripts/rkjxt_note_0920.py
    itq run scripts/rkjxt_note_0920.py --commit
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockItem  # noqa: E402

COMMIT = "--commit" in sys.argv

STALE_START = "LOCATION UNRESOLVED"
STALE_END = "waiting room, not a place."

NEW = """LOCATION — the 2026-08-27 either/or is ANSWERED, 2026-09-20, and the answer was BOTH.
Scott, counting MC-T3 with the drawer open: "1 rkjxt, the other got used on the
MFD build already." So one was in the mobile cart and one was fitted — but
fitted into the G1000 MFD (build #2), NOT into the sim's own G1000 panel, which
is the candidate the old note named. The consumed unit is allocated to BO-0020
and leaves stock when that build closes.

STILL OPEN: where the surviving one goes. It was physically in MC-T3, but this
row has always been recorded at #502, the waiting room — so when MC-T3 was
emptied to SLN/Florida Staging today, the sweep moved the rows that SAID MC-T3
and never saw this one. Ask before filing: the rest of the G1000 build #3 kit
went to Florida Staging, and it is not established that this switch belongs
with it."""


def main():
    si = StockItem.objects.get(pk=9)
    notes = si.notes or ""
    i = notes.find(STALE_START)
    j = notes.find(STALE_END)
    if i < 0 or j < 0:
        print("anchors not found — nothing done")
        return 1
    j += len(STALE_END)
    new_notes = notes[:i] + NEW + notes[j:]

    print("=== REMOVING ===")
    print(notes[i:j][:400])
    print("\n=== INSERTING ===")
    print(NEW)

    if not COMMIT:
        print("\nDRY RUN — add --commit")
        return 0

    si.notes = new_notes
    si.save()
    # Verify: .save() on this install has reported success and written nothing.
    si.refresh_from_db()
    if STALE_START in (si.notes or "") or "ANSWERED, 2026-09-20" not in (si.notes or ""):
        print("save() did not stick — falling back to queryset update()")
        StockItem.objects.filter(pk=9).update(notes=new_notes)
        si.refresh_from_db()
    ok = STALE_START not in (si.notes or "") and "ANSWERED, 2026-09-20" in (si.notes or "")
    print(f"\nVERIFIED: {ok}")
    return 0 if ok else 1


sys.exit(main())
