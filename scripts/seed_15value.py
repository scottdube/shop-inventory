"""Seed the 15-value 200pc electrolytic kit from its printed lid.

Photographed 2026-08-23. The lid reads "15 Value 200 pcs Electronic Capacitor
Kit Box" and lists every value with its body size and count; they sum to
exactly 200, and each one matches a part already in the catalogue.

This kit is where the "extra" 4x7 parts came from. The 2026-08-18 note that
blocked seeding said 15 parts carried a 4x7 body while the 10-value 4x7 kit
claimed only 10 values -- and treated that as a contradiction. It was not:
those parts belong to THIS box. Both lids together resolve it.

Two values appear in more than one kit -- 47uF 16V 4x7 is also 30 pcs in the
Xuansn box, and most of the small values are also in the 10-value 4x7 box.
That is fine and expected: a part can be in two places, and each location
carries its own row. Summing the rows gives the shop total.

[ESTIMATE], no stocktake_date: a printed card is not a count.

    itq run scripts/seed_15value.py            # dry run
    itq run scripts/seed_15value.py --commit
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

KIT = "Kit - 15-Value Electrolytic"

# Read straight off the lid, left to right, top to bottom.
VALUES = [
    (673, "0.1uF 50V",  15), (674, "0.22uF 50V", 15), (675, "0.47uF 50V", 15),
    (676, "1uF 50V",    15), (677, "2.2uF 50V",  15), (678, "3.3uF 50V",  15),
    (679, "4.7uF 50V",  15), (680, "10uF 25V",   15), (681, "22uF 25V",   15),
    (682, "33uF 16V",   15), (683, "47uF 16V",   10), (684, "47uF 25V",   10),
    (685, "100uF 10V",  10), (686, "100uF 25V",  10), (687, "220uF 10V",  10),
]

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.filter(name=KIT).first()
if not loc:
    sys.exit(f"no such location: {KIT}")
print(f"location: {loc.pathstring}")
print(f"{len(VALUES)} values, {sum(q for _, _, q in VALUES)} pieces on the lid\n")

NOTE = ("[ESTIMATE] {q} pcs when new, read from the kit's PRINTED LID, "
        "photographed 2026-08-23. The 15 values sum to exactly the 200 the lid "
        "claims. NOT a count - the box has been drawn from, so treat this as an "
        "UPPER BOUND. No stocktake date on purpose, so the never-counted report "
        "keeps surfacing it until a compartment is tallied. This part may also "
        "appear in other kits; sum the rows for the shop total.")

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

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}: {wrote} seeded, "
      f"{skipped} already there, {failed} failed")
sys.exit(1 if failed else 0)
