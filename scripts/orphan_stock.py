#!/usr/bin/env python3
"""Stock rows with NO location at all — the invisible kind of unfiled.

There are two kinds of unfiled and only one of them is visible.

  "Unfiled - Machine Shop" is a PLACE. It appears when you browse, its own
  description says it should trend toward empty, and looking at it is a thing
  somebody actually does.

  location = NULL appears in no location's contents. Nothing lists it, nothing
  browses it, and nothing will ever prompt anyone to deal with it. A row can sit
  there for the life of the install.

Found 2026-08-31 when Scott asked why the ZVS kit parts were "ending up as
unfiled". They were not unfiled — they were nowhere, which is why nothing had
ever surfaced them. 41 rows across 11 categories had accumulated:

  29  the McMaster import — route_loc() returns None for a description it cannot
      classify and the row is created anyway. The importer prints "(no location)"
      in its routing summary, which is a report, not a mechanism.
   8  the ZVS/shrink-fit kit, from an ad-hoc session script: catalogue the part
      now, decide the physical home later, and "later" had no hook.
   4  older singles

An item installed into another (belongs_to set) is NOT an orphan — a stud in a
holder or a LiPo in a probe is exactly where it should be.

    itq run scripts/orphan_stock.py
    itq run scripts/orphan_stock.py --by-source
"""
import argparse
import os
import sys
from collections import Counter, defaultdict

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockItem  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--by-source", action="store_true",
                help="group by part creation date, which usually identifies the import")
a = ap.parse_args()

orphans = (StockItem.objects.filter(location__isnull=True, belongs_to__isnull=True)
           .select_related("part", "part__category"))
n = orphans.count()

installed = StockItem.objects.filter(location__isnull=True,
                                     belongs_to__isnull=False).count()

print(f"STOCK ROWS WITH NO LOCATION: {n}")
print(f"  (plus {installed} row(s) with no location that ARE installed via "
      f"belongs_to — correctly placed, not counted here)")

if not n:
    print("\n  OK  nothing is nowhere.")
    sys.exit(0)

if a.by_source:
    groups = defaultdict(list)
    for si in orphans:
        groups[str(si.part.creation_date)].append(si)
    print("\nBY PART CREATION DATE — a cluster is usually one import or one session:")
    for d in sorted(groups):
        rows = groups[d]
        print(f"\n  {d}   {len(rows)} row(s)")
        for si in sorted(rows, key=lambda x: x.part.name):
            print(f"      #{si.pk:>4} qty {si.quantity:>8g}  {si.part.name[:58]}")
else:
    print("\nBY CATEGORY:")
    for cat, c in Counter(
            (si.part.category.pathstring if si.part.category else "(no category)")
            for si in orphans).most_common():
        print(f"   {c:>3}  {cat}")
    print("\nROWS:")
    for si in orphans.order_by("part__name"):
        print(f"   #{si.pk:>4} qty {si.quantity:>8g}  {si.part.name[:58]}")

print(f"\n!! {n} row(s) are in no place at all. Each one answers YES to "
      f"\"do I have one?\"\n   and NO to \"where is it?\", which is the worst "
      f"pair of answers a stock\n   system can give. Give each a real location, "
      f"or park it somewhere VISIBLE\n   like \"Unfiled - <area>\" so browsing "
      f"the shop surfaces it.")
sys.exit(1)
