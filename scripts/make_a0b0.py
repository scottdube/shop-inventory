"""Create A0 and B0 — the two Akro-Mils 10124 all-large cabinets.

Ordered 2026-08-22, arriving Tuesday 2026-08-25. Run this once they are on the
wall, not before: creating locations for cabinets that are still in a box means
the record claims a place exists that does not.

    itq run scripts/make_a0b0.py            # dry run
    itq run scripts/make_a0b0.py --commit

**Why A0/B0 and not A4/B4.** The letter is the ROW and the number is the column,
left to right — settled 2026-08-22 when Scott's expansion plan turned out to
grow DOWNWARD (a third row C below B, where the plywood table is) rather than
rightward. The new pair hangs to the LEFT of A1/B1, so they are column zero.
A0/B0 reads left-to-right in order, renumbers nothing, invents no letter, and
leaves all 324 existing labels valid. Zero-indexing the first column is a
one-time exception that never has to extend to A-1.

**Geometry.** A 10124 is 24 drawers in a 6x4 grid, all LARGE — the same drawer
as the B wall's rows 5-7, so drawers are interchangeable with those. Shell is
20 x 6-3/8 x 15-13/16 in, identical to the 10164s that make up the A wall, so
two stacked are 31-5/8 in and sit level with the A row over the B row.

**Drawer class CONFIRMED 2026-08-25**, on arrival, by Scott: *"They are
identical size to the, uh, other bins."* The cabinets were delivered that day and
compared against the wall in the shop, which is what this check was waiting for —
the 62 x 4-1/2 x 2-3/16 figure had come from Walmart's AI-generated spec block
rather than from Akro-Mils, and returns are free for 90 days precisely so a
mismatch could be sent back.

Recorded as a COMPARISON against the existing large drawers, not a tape
measurement — which is the right evidence for the question actually being asked,
"do these interchange with B rows 5-7". If a future session needs the absolute
dimensions rather than the match, that is still unmeasured.
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockLocation      # noqa: E402

ROWS, COLS = 6, 4
SIZE = "[6 x 4-9/16 x 2-3/16 in, large]"

CABINET = (
    "Akro-Mils 10124 — 24 drawers, ALL LARGE ({r} rows x {c} wide, "
    "6 x 4-9/16 x 2-3/16 in each). Bought 2026-08-22, hung {when}.\n\n"
    "**Column ZERO: this hangs to the LEFT of {right}.** The letter is the row "
    "and the number is the column left to right, so the new leftmost cabinet is "
    "0 rather than 4. Renaming the existing wall to make it 1 would have meant "
    "relabelling 324 drawers and invalidating every printed QR in the shop.\n\n"
    "Drawers here are interchangeable with the B wall's large rows 5-7 — same "
    "part, same shell as the A-wall 10164s.\n\n"
    "**{purpose}**"
)

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--when", default="2026-08-25", help="the day they went on the wall")
a = ap.parse_args()

wall = StockLocation.objects.get(name="Bin Wall")
plan = [
    ("A0", "A1", "Top row, left end. Purpose not yet assigned — large drawers "
                 "were the scarce class (11 empty of 35 shop-wide when these "
                 "were bought), so decide what earns them rather than filling "
                 "them with whatever is nearest."),
    ("B0", "B1", "Middle row, left end. B1 and B2 are the METRIC and IMPERIAL "
                 "McMaster cabinets; if this becomes their overflow, keep the "
                 "thread-system split — it is the wall's organising principle "
                 "and nothing records it except the cabinet descriptions."),
]

made = skipped = 0
for name, right_of, purpose in plan:
    cab = StockLocation.objects.filter(name=name, parent=wall).first()
    if cab:
        print(f"  {name}: already exists — skipping")
        skipped += 1
    else:
        print(f"  {name}: create, {ROWS}x{COLS} = {ROWS*COLS} large drawers")
        if a.commit:
            cab = StockLocation.objects.create(
                name=name, parent=wall,
                description=CABINET.format(r=ROWS, c=COLS, when=a.when,
                                           right=right_of, purpose=purpose))
            made += 1
    for r in range(1, ROWS + 1):
        for c in range(1, COLS + 1):
            dn = f"{name}-R{r}C{c}"
            if cab and StockLocation.objects.filter(name=dn, parent=cab).exists():
                continue
            if a.commit and cab:
                StockLocation.objects.create(name=dn, parent=cab, description=SIZE)
    if a.commit and cab:
        n = StockLocation.objects.filter(parent=cab).count()
        print(f"        {n} drawers created")

if not a.commit:
    print(f"\n  DRY RUN — would create {2 - skipped} cabinet(s) and "
          f"{(2 - skipped) * ROWS * COLS} drawers. Add --commit")
    raise SystemExit

stale = [l.name for l in StockLocation.objects.all()
         if (l.pathstring or "") != l.construct_pathstring()]
print(f"\n  created {made} cabinet(s); stale pathstrings: {stale or 'none'}")
print("\n  NEXT:")
print("    1. itq run scripts/link_barcodes.py --commit      link the QR data")
print("    2. itq run scripts/make_labels_avery.py A0 B0     or the 62mm roll")
print("    3. itq run scripts/mark_empty.py --cabinet A0 --commit   (and B0)")
print("       a NEW cabinet is known-empty, but only the person who hung it")
print("       can say so — without the stamp the wall gauge reads the 48 as")
print("       unknown space and falls 12 points for adding capacity")
print("    4. drawer class already confirmed 2026-08-25 by comparison —")
print("       nothing to measure unless absolute dimensions are needed")
