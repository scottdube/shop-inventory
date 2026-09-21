"""Queue D, 2026-09-21: which empty-keyword rows are LIVE parts?

kw_dump.py lists the 54 rows with empty keywords but not their active flag, and
that flag decides whether a row should be given keywords at all. Most of the 54
are merge receipts and refund/not-inventory tombstones, and making a tombstone
findable in plain-English search is worse than leaving it blank -- a retired
duplicate that answers a search reads as a live part (docs/TRAPS.md, "inactive
parts are merge receipts").

So: print the flag, and let the write step take only the live ones.
"""
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

EMPTY = Q(keywords="") | Q(keywords__isnull=True)
rows = Part.objects.filter(EMPTY).order_by("pk")

live = dead = 0
for p in rows:
    flag = "LIVE" if p.active else "----"
    live += p.active
    dead += not p.active
    if p.active:
        print(f"{flag} {p.pk:5d} | {str(p.category):34s} | {p.name[:62]}")
        print(f"            desc: {(p.description or '')[:150]}")

print(f"\nempty-keyword rows: {rows.count()}  live={live}  inactive={dead}")
