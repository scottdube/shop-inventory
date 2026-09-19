#!/usr/bin/env python3
"""Counts from Scott 2026-09-19: 1 fuse holder (#252), 95 plugs (#1235).

BOTH PRINTED PACK FIGURES WERE WRONG TODAY, AND SO WAS THE THIRD.

    keystone bag   printed 25    counted 15    -40%
    plug jar       printed 100   counted 95     -5%
    fuse holder    a 2016 3-pack in the record; the unit in hand is not from
                   it at all, so the pack figure was not merely wrong, it was
                   about a different object

Three chances for the packaging to tell the truth, three misses. Two of them
would have been believed: 100 is a plausible number for a sealed-looking jar,
and a 3-pack with no stock row plus a physical holder is a story that writes
itself. The -5% one is the dangerous one -- a figure close enough to right
that nobody would ever re-check it.

#252 GOES TO L2-D2, AND THAT IS STILL A PROPOSAL. Twice today a location that
matched on category and size class turned out to be physically full (B3-R6C4,
then B-03). L2-D2 holds #346's blade fuse kit and #1203's glass holders, so it
is the right drawer by theme, and ONE inline holder is small enough that the
risk is low rather than zero. Filing it and saying so, rather than asking a
third time about a single part -- but the record says it was not eyeballed.

    itq run scripts/count_plugs_and_holder.py [--commit]
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

JOBS = [
    dict(part=252, loc="SLN/Laser Area/L2/L2-D2", qty=1,
         anchor="**Count and location still open.** Nobody has counted what is in hand, and `L2-D2` is the proposed home (it holds #346 and #1203) but has not been checked for space.",
         add="""**COUNTED 2026-09-19 BY SCOTT: 1.** One holder, the one that came sealed in the bag with [#1233]. This is a tally of what is in hand, not a pack figure — and note again that it says **nothing** about the three from the 2016 order.

**Filed in `L2-D2`, which was NOT eyeballed for space.** It is the right drawer by theme: [#346]'s ATO/ATC blade fuse kit and [#1203]'s glass holders are both in it, and the fuses this holder takes are there. Twice on 2026-09-19 a drawer that matched on category and size class turned out to be full (`B3-R6C4`, then bin `B-03`), so this is recorded as a proposal acted on, not a verified fit. One inline holder is small enough to make that a reasonable bet and the bet is written down."""),
    dict(part=1235, loc="SLN/Laser Area/LW3/LW3-S1/B-04", qty=95,
         anchor="**NO COUNT. The jar says 100 and that is a PACK SIZE.** Nobody has counted it. The keystone bag next to it said 25 and held 15 — same class of item, same day, and the printed figure was wrong by forty percent.",
         add="""**COUNTED 2026-09-19 BY SCOTT: 95. The jar says 100.** Five short — and five is the dangerous kind of wrong, because 95 out of a printed 100 is close enough that nobody would ever think to re-check it. The keystone bag beside it said 25 and held 15.

**Both printed pack figures checked on 2026-09-19 were wrong.** That is the whole case for the standing rule: a pack size is a supplier fact about what left the factory, and the moment a container is opened it stops being a count. Treat a printed figure as an upper bound at best.

95 is a tally, not an estimate — no `[ESTIMATE]` marker."""),
]

rows = []
for j in JOBS:
    p = Part.objects.get(pk=j["part"])
    loc = StockLocation.objects.get(pathstring=j["loc"])
    found = j["anchor"] in (p.notes or "")
    existing = StockItem.objects.filter(part=p, location=loc).first()
    print(f"#{p.pk} {p.name[:50]:50s} -> {loc.name:8s} qty {j['qty']}")
    print(f"     anchor {found}   existing row {existing.pk if existing else 'none'}"
          f"   default_loc {p.default_location.name if p.default_location else 'NONE'}")
    if not found:
        print("     ANCHOR MISSING — refusing a half edit."); sys.exit(1)
    rows.append((p, loc, j))

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

for p, loc, j in rows:
    Part.objects.filter(pk=p.pk).update(
        notes=p.notes.replace(j["anchor"], j["add"]), default_location=loc)
    si = StockItem.objects.filter(part=p, location=loc).first()
    if si is None:
        si = StockItem.objects.create(part=p, location=loc, quantity=j["qty"])
    else:
        StockItem.objects.filter(pk=si.pk).update(quantity=j["qty"])
    p.refresh_from_db(); si.refresh_from_db()
    print(f"\n#{p.pk} {p.name}")
    print(f"    default_location {p.default_location.pathstring}")
    print(f"    stock [{si.pk}] qty {si.quantity:g} @ {si.location.pathstring}"
          f"  {'ok' if float(si.quantity) == j['qty'] else '!! WRONG'}")
    print(f"    old 'no count' gone  {j['anchor'] not in p.notes}")
    print(f"    counted-by-Scott     {'COUNTED 2026-09-19 BY SCOTT' in p.notes}")
