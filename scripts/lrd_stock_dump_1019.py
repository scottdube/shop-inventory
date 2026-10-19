"""Dump every stock row under the LRD location tree, grouped by part category.

Read-only. Written 2026-10-19 to build a wish list for the HoT Small Computers
"My Trash, Your Treasure" parts swap (Oct 27): what the LRD shop already holds,
so the list targets gaps rather than duplicates.

Usage:  itq run scripts/lrd_stock_dump_1019.py
"""

import os
import sys
from collections import defaultdict

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockItem, StockLocation  # noqa: E402

roots = StockLocation.objects.filter(parent__isnull=True)
print("roots:", [(r.pk, r.name) for r in roots])
lrd = StockLocation.objects.get(parent__isnull=True, name="LRD")
locs = lrd.get_descendants(include_self=True)

rows = StockItem.objects.filter(location__in=locs).select_related("part", "part__category", "location")
by_cat = defaultdict(list)
for s in rows:
    cat = s.part.category.pathstring if s.part.category else "(uncategorized)"
    by_cat[cat].append(s)

print(f"LRD stock rows: {rows.count()}  (root pk {lrd.pk})")
for cat in sorted(by_cat):
    print(f"\n## {cat}")
    for s in sorted(by_cat[cat], key=lambda x: x.part.name.lower()):
        loc = s.location.pathstring.replace("LRD/", "", 1)
        print(f"  {float(s.quantity):g}\t{s.part.name[:80]}\t[{loc}]")
