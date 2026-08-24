"""Audit the [ESTIMATE] marker: where it lives, and where it contradicts itself.

Read-only. Written after the overnight-import project's brief reported ZERO
[ESTIMATE] records by querying Part.description -- the marker is on
StockItem.notes. That correction turned up rows carrying BOTH the marker and a
stocktake_date, which the convention says cannot happen.

The question this answers is not "how many are wrong today" but "is anything
stripping the marker when a count happens" -- because if not, the count grows
with every drawer walked.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part                                      # noqa: E402
from stock.models import StockItem                                # noqa: E402

marked = StockItem.objects.filter(notes__icontains="[ESTIMATE]")
print(f"StockItem.notes  carrying [ESTIMATE]: {marked.count()}")
print(f"Part.description carrying [ESTIMATE]: "
      f"{Part.objects.filter(description__icontains='[ESTIMATE]').count()}"
      "   <- the field the brief queried")

dated = marked.exclude(stocktake_date__isnull=True).order_by("pk")
print(f"\nBOTH marker and stocktake_date -- convention says impossible: {dated.count()}")
for si in dated.select_related("part", "location"):
    loc = si.location.name if si.location else "(unlocated)"
    print(f"  #{si.pk:4}  {si.stocktake_date}  {loc:16} "
          f"qty {float(si.quantity):>7.10g}  {si.part.name[:40]}")

undated = marked.filter(stocktake_date__isnull=True).count()
print(f"\n[ESTIMATE] with no stocktake_date (correct state): {undated}")
print(f"counted rows overall (any stocktake_date): "
      f"{StockItem.objects.exclude(stocktake_date__isnull=True).count()} "
      f"of {StockItem.objects.count()}")
