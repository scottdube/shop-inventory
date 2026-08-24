"""Give the FR-301 desoldering nozzles a home: A3-R1C2.

Scott, 2026-08-24: the nozzles go in the Akro-Mils bins — this 1.3mm one and
the 0.8mm sibling #87.

Drawer chosen rather than asked about: B3 is fully allocated, A3 has a block of
drawers VERIFIED EMPTY on 2026-08-23, and R1C2 is top row on the cabinet that
sits immediately left of the electronics bench. A bench consumable belongs at
eye level, not in a bottom row.

This sets default_location only. It creates NO stock, because default_location
is "where a spare goes home" and is a policy, while a stock row is a claim that
something is physically in the drawer. Those two are exactly the pair the SHT31
failure conflated, so they are written by different scripts on purpose.

    itq run scripts/nozzle_drawer.py
    itq run scripts/nozzle_drawer.py --commit
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part                      # noqa: E402
from stock.models import StockLocation            # noqa: E402

DRAWER = "A3-R1C2"
PARTS = (213, 87)
DESC = ("SOLDERING — Hakko FR-301 / FR-4101 desoldering nozzles. N61-06 1.3mm "
        "and N61-07 0.8mm. Reach for these when a through-hole joint has to come "
        "apart without lifting the pad: the gun melts and vacuums in one motion, "
        "where wick-and-iron means holding heat on the pad far longer. Nozzle "
        "bore must be a little larger than the lead — 0.8mm for signal pins, "
        "1.3mm for power pins, connector posts and anything on a ground plane. "
        "Established 2026-08-24; drawer was VERIFIED EMPTY 2026-08-23. "
        "[6 x 2-7/32 x 1-9/16 in, small]")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

locs = list(StockLocation.objects.filter(name__iexact=DRAWER))
assert len(locs) == 1, f"{DRAWER} matched {len(locs)}"
loc = locs[0]

print(f"drawer {loc.pathstring}")
print(f"  now : {(loc.description or '')[:80]}")
print(f"  ->  : {DESC[:80]}...")
print(f"  stock items currently in it: {loc.stock_items.count()}")
if loc.stock_items.exists():
    print("  !! not empty — refusing, the description would be a lie")
    raise SystemExit(1)

for pk in PARTS:
    p = Part.objects.get(pk=pk)
    print(f"\n#{pk} {p.name[:58]}")
    print(f"   default_location {p.default_location} -> {loc.pathstring}")
    print(f"   stock rows: {p.stock_items.count()}  (untouched by this script)")

if not a.commit:
    print("\nDRY RUN — add --commit")
    raise SystemExit

StockLocation.objects.filter(pk=loc.pk).update(description=DESC)
assert StockLocation.objects.get(pk=loc.pk).description == DESC, "desc did not stick"
print(f"\nOK  {DRAWER} described")

for pk in PARTS:
    Part.objects.filter(pk=pk).update(default_location=loc)
    assert Part.objects.get(pk=pk).default_location_id == loc.pk, f"#{pk} did not stick"
    print(f"OK  #{pk} default_location -> {loc.pathstring}")
