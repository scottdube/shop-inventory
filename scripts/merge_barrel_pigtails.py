#!/usr/bin/env python3
"""Add 2 female and 2 male DC barrel pigtails to the existing rows.

Scott produced four more on the bench 2026-09-19: two female jacks and two
male plugs, red/black flying leads. Both parts already exist.

    #1200 FEMALE 5.5 x 2.1  10 -> 12   @ B0-R1C3
    #1201 MALE   5.5 x 2.1  14 -> 16   @ B0-R1C3

MERGE, NOT NEW ROWS. Once goods are in inventory the shelf answers "how many
do I have" in one number. See CLAUDE.md.

SIZE WAS ASKED, NOT ASSUMED, AND IT WAS THE WHOLE QUESTION. Both parts carry
a warning in their own notes that 5.5 x 2.5 mm looks identical and will seem
to fit while making intermittent centre-pin contact -- and the shop owns a
5.5 x 2.5 supply (PS-010 #1219), so a 2.5 pigtail on this bench is entirely
plausible. Had these been 2.5 they would be DIFFERENT PARTS and merging them
would have poisoned two good rows with an item that fails intermittently
months later. Scott confirmed 5.5 x 2.1.

COUNT WAS ASKED, NOT READ OFF THE PHOTO. Four are visible in frame. Four is
also the answer, which is exactly why asking looks unnecessary and is not:
the photo could not have shown a fifth on the far side of the towel, and
three printed pack figures were wrong earlier the same day.

WHAT IS NOT CLAIMED: where these four came from. #1200 was 10 of a 20-pack
with "some went to LRD", and #1201 was 14 of a 20-pack with 6 unaccounted, so
stragglers from those same packs is the obvious story -- and obvious is not
established. A Home Depot label is visible on the bench in the photo, which
points the other way, and it may belong to something else entirely. The
balance lines stay as they are.

    itq run scripts/merge_barrel_pigtails.py [--commit]
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402
from stock.models import StockItem  # noqa: E402

COMMIT = "--commit" in sys.argv

ADD_NOTE = """

**+2 added 2026-09-19.** Scott brought {n} more to the bench; row goes {a} -> {b}. **Size confirmed 5.5 x 2.1 mm by Scott before merging, not assumed from appearance** — the look-alike warning above is the reason, and the shop owns a 5.5 x 2.5 supply ([PS-010 #1219]) so a 2.5 pigtail here was a real possibility. A 2.5 merged into this row would fail intermittently months later with nothing pointing back at the merge.

**Origin of these {n} is NOT established.** Stragglers from the same 20-piece pack is the obvious reading and stays unwritten — the balance line above is unchanged. A Home Depot label was on the bench in the photo, which points elsewhere and may belong to something else entirely."""

JOBS = [
    dict(pk=1200, add=2, old=10, new=12,
         anchor='COUNTED 10 by Scott 2026-09-14.',
         replace='COUNTED 10 by Scott 2026-09-14 (superseded — see the +2 below).'),
    dict(pk=1201, add=2, old=14, new=16,
         anchor='COUNTED 14 by Scott 2026-09-14, from a 20-piece pack.',
         replace='COUNTED 14 by Scott 2026-09-14, from a 20-piece pack (superseded — see the +2 below).'),
]

rows = []
for j in JOBS:
    p = Part.objects.get(pk=j["pk"])
    si = StockItem.objects.filter(part=p).first()
    hit = j["anchor"] in p.notes
    print(f"#{p.pk} {p.name[:54]:54s}")
    print(f"     row [{si.pk}] qty {si.quantity:g} @ {si.location.name}"
          f"   {j['old']} + {j['add']} -> {j['new']}")
    print(f"     anchor {'ok' if hit else 'MISS'}   rows for part: "
          f"{StockItem.objects.filter(part=p).count()}")
    if not hit:
        print("ANCHOR MISSING — refusing a half edit."); sys.exit(1)
    if float(si.quantity) != j["old"]:
        print(f"QTY IS NOT {j['old']} — something changed, stop."); sys.exit(1)
    if StockItem.objects.filter(part=p).count() != 1:
        print("MORE THAN ONE ROW — merge target is ambiguous, stop."); sys.exit(1)
    rows.append((p, si, j))

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

for p, si, j in rows:
    n = p.notes.replace(j["anchor"], j["replace"]) + ADD_NOTE.format(
        n=j["add"], a=j["old"], b=j["new"])
    Part.objects.filter(pk=p.pk).update(notes=n)
    StockItem.objects.filter(pk=si.pk).update(quantity=j["new"])
    p.refresh_from_db(); si.refresh_from_db()
    print(f"\n#{p.pk} {p.name}")
    print(f"    row [{si.pk}] qty {si.quantity:g} @ {si.location.pathstring}"
          f"  {'ok' if float(si.quantity) == j['new'] else '!! WRONG'}")
    print(f"    rows for part     {StockItem.objects.filter(part=p).count()}  (must be 1)")
    print(f"    old count marked  {'superseded' in p.notes}")
    print(f"    +2 recorded       {'+2 added 2026-09-19' in p.notes}")
    print(f"    size confirmed    {'Size confirmed 5.5 x 2.1 mm by Scott' in p.notes}")
    print(f"    origin unclaimed  {'Origin of these 2 is NOT established' in p.notes}")
