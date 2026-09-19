#!/usr/bin/env python3
"""Retract the "nothing in the shop terminates these" claim from #1234/#1235.

Scott, 2026-09-19: "I have multiple punchdown tools and crimpers for this
stuff."

I WROTE A CATALOGUE ABSENCE INTO THE RECORD AS A FACT ABOUT THE SHOP, IN BOLD,
WITH A WARNING GLYPH -- for the second time in the same session and on the
same subject. The first time, I said the catalogue had "zero patch cables,
RJ45 plugs, keystones or an RJ45 crimper"; Scott produced a bag of keystones
and I corrected it in chat. Then I put the same shape of claim into two
permanent part notes an hour later.

The search itself was sound and is worth keeping: nothing matching punchdown,
110 tool, keystone, wall plate, patch panel, krone, IDC or crimper is in
InvenTree, uncapped, whole catalogue. What was wrong was the sentence built on
top of it. "The catalogue has no punchdown tool" and "the shop has no
punchdown tool" are different claims and only one of them was checked.

Correcting it in chat was not enough the first time BECAUSE THE FIX HAS TO
LAND WHERE THE CLAIM LIVES. A chat correction expires with the session; the
part note is what somebody reads in a year.

WHAT IS ACTUALLY TRUE AND IS A REAL GAP: the tools exist physically and are
NOT in InvenTree. That is worth recording -- not as "we need to buy one" but
as "the catalogue cannot answer this question", which is the honest version
and points at cataloguing rather than purchasing.

NOT ASSUMED: whether any of those crimpers is a PASS-THROUGH crimper with an
integrated flush cutter. Scott said "crimpers for this stuff" and that does
not resolve it. #1235 keeps the requirement, restated as something to check
against the tools on hand rather than as an absence.

    itq run scripts/retract_no_tools_claim.py [--commit]
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

COMMIT = "--commit" in sys.argv

NO_TOOLS = """**⚠ NOTHING IN THE SHOP TERMINATES THIS.** Searched the whole catalogue 2026-09-19 for punchdown, 110 tool, keystone, wall plate, patch panel, krone, IDC and crimper: **no punchdown tool, no RJ-45 crimper of any kind, no patch panel, no wall plates.**"""

CORRECTED = """**THE TOOLS EXIST — THEY ARE JUST NOT CATALOGUED.** Scott, 2026-09-19: *"I have multiple punchdown tools and crimpers for this stuff."*

**Retracted, same day.** This note previously read "⚠ NOTHING IN THE SHOP TERMINATES THIS", in bold, off a catalogue search. The search was sound — nothing matching punchdown, 110 tool, keystone, wall plate, patch panel, krone, IDC or crimper is in InvenTree, whole catalogue, uncapped. **The sentence built on top of it was not.** "The catalogue has no punchdown tool" and "the shop has no punchdown tool" are different claims, and only the first one was ever checked.

**So the gap is a CATALOGUING gap, not a purchasing one.** Nothing needs buying to terminate these. What is missing is that the catalogue cannot answer "do we own a punchdown tool?" — it will say no, and be wrong."""

EDITS = [
    dict(part=1234,
         subs=[(NO_TOOLS + " Fifteen jacks and nothing to press them with or land them in.",
                CORRECTED),
               ("**And a keystone is only half a termination.** The other half is a wall plate, surface box or patch panel, and the catalogue has none. Budget those with the tool, not after it arrives.",
                "**A keystone is only half a termination.** The other half is a wall plate, surface box or patch panel. The catalogue has none — but the catalogue also said there was no punchdown tool, so that is a statement about InvenTree and not about the shop. **Ask before ordering any.**")]),
    dict(part=1235,
         subs=[("""**So the missing tool is now specific, not generic.** "An RJ-45 crimper" does not cover this jar. """ + NO_TOOLS,
                """**So the tool requirement is specific, not generic** — and that is the part still worth checking. Scott has multiple crimpers (2026-09-19), which settles the generic question and not this one: **an ordinary RJ-45 crimper does not crimp these.** Confirm one of the crimpers on hand is a pass-through type with the integrated flush cutter before starting a run with this jar.

""" + CORRECTED)]),
]

for e in EDITS:
    p = Part.objects.get(pk=e["part"])
    print(f"#{p.pk} {p.name[:56]}")
    for old, _ in e["subs"]:
        hit = old in p.notes
        print(f"    anchor {'ok  ' if hit else 'MISS'}  {old[:62]}...")
        if not hit:
            print("\nANCHOR MISSING — refusing a half edit."); sys.exit(1)

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

for e in EDITS:
    p = Part.objects.get(pk=e["part"])
    n = p.notes
    for old, new in e["subs"]:
        n = n.replace(old, new)
    Part.objects.filter(pk=p.pk).update(notes=n)
    p.refresh_from_db()
    print(f"\n#{p.pk} {p.name}")
    print(f"    false claim gone   {'NOTHING IN THE SHOP TERMINATES' not in p.notes}")
    print(f"    retraction filed   {'Retracted, same day' in p.notes}")
    print(f"    cataloguing gap    {'CATALOGUING gap' in p.notes}")
    if p.pk == 1235:
        print(f"    pass-through open  {'pass-through type with the integrated flush cutter' in p.notes}")
