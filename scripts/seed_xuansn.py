"""Seed the Xuansn 18-value electrolytic kit from its stated breakdown.

Pending since 2026-08-18. The blocker was that seeding by DIVISION would put
stock on values that are not in the box -- which is exactly what went wrong
with the 4x7 kit, whose printed lid turned out to name a value it does not
contain.

This is not a division. Every value already carries its own figure, recorded
per part as "N pcs when new", and they reconcile exactly:

    18 values, 270 pieces -- the same 18 and 270 the kit itself claims.

An arithmetic coincidence at that precision is not a coincidence; the
breakdown came from the vendor's own listing. That makes these CARD-STATED
figures, the middle evidence tier, and card-stated is honest to record as long
as it is recorded AS an estimate.

So: every row is written `[ESTIMATE]` with **no stocktake_date**, which is what
keeps them on the never-counted report until somebody actually tallies a bag.
Nobody has counted these. The kit has also been drawn from since it was new --
at minimum a 470uF 25V is about to leave for the AC Wall Adapter build -- so
"when new" is an upper bound, and the note says so.

#662 is deliberately NOT used: it is the retired duplicate of #683. Seeding a
deactivated part would put 30 capacitors somewhere nothing looks.

    itq run scripts/seed_xuansn.py            # dry run
    itq run scripts/seed_xuansn.py --commit
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part                                      # noqa: E402
from stock.models import StockItem, StockLocation                 # noqa: E402

KIT = "Kit - Xuansn Electrolytic"

# (part pk, name fragment that must match, qty when new)
# The fragment is a guard: a bare pk list is one renumbering away from seeding
# the wrong capacitor, and these differ by a single character.
VALUES = [
    (655, "4.7uF 50V",   20), (656, "4.7uF 100V",  20),
    (657, "4.7uF 250V",  15), (658, "4.7uF 400V",  15),
    (661, "4.7uF 450V",  15),
    (683, "47uF 16V",    30),   # NOT #662 - that is the retired duplicate
    (663, "47uF 25V",    20), (664, "47uF 35V",    20),
    (667, "47uF 50V",    20), (659, "47uF 160V",   10),
    (665, "47uF 200V",    5), (671, "47uF 250V",    5),
    (668, "470uF 10V",   20), (669, "470uF 16V",   15),
    (670, "470uF 25V",   15), (660, "470uF 35V",   10),
    (666, "470uF 50V",   10), (672, "470uF 63V",    5),
]

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.filter(name=KIT).first()
if not loc:
    sys.exit(f"no such location: {KIT}")
print(f"location: {loc.pathstring}")
print(f"{len(VALUES)} values, {sum(q for _, _, q in VALUES)} pieces claimed\n")

NOTE = ("[ESTIMATE] Quantity is {q} pcs when new, read from the kit's PRINTED "
        "LID, photographed 2026-08-23. Every one of the 18 values, its quantity "
        "AND its body size match the catalogue exactly, and they sum to the 270 "
        "the lid claims - so this is a card-stated figure, not a division. It is "
        "still not a count: the kit has been drawn from since it was new, so "
        "treat it as an UPPER BOUND. No stocktake date on purpose, so the "
        "never-counted report keeps surfacing this until a compartment is "
        "actually tallied.")

wrote = skipped = failed = 0
for pk, frag, qty in VALUES:
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"  #{pk}: NO SUCH PART"); failed += 1; continue
    if frag.lower() not in p.name.lower():
        print(f"  #{pk}: name guard FAILED - {frag!r} not in {p.name!r}")
        failed += 1; continue
    if not p.active:
        print(f"  #{pk}: INACTIVE - refusing to seed a retired part")
        failed += 1; continue
    if StockItem.objects.filter(part=p, location=loc).exists():
        print(f"  #{pk} {p.name[:44]:46} already seeded"); skipped += 1; continue

    print(f"  #{pk} {p.name[:44]:46} {qty:>3}")
    wrote += 1
    if not a.commit:
        continue
    si = StockItem.objects.create(part=p, location=loc, quantity=qty,
                                  notes=NOTE.format(q=qty))
    again = StockItem.objects.filter(pk=si.pk).first()
    ok = (again and float(again.quantity) == qty
          and again.location_id == loc.pk and again.stocktake_date is None)
    if not ok:
        print("       WRITE DID NOT VERIFY"); failed += 1; wrote -= 1
        continue
    if p.default_location_id != loc.pk:
        Part.objects.filter(pk=pk).update(default_location=loc)

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}: {wrote} seeded, "
      f"{skipped} already there, {failed} failed")
sys.exit(1 if failed else 0)
