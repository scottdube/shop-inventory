"""Audit the [ESTIMATE] marker: where it lives, and where it contradicts itself.

Read-only.

**Use startswith, never icontains.** The convention is that `[ESTIMATE]` OPENS
the note. A note that mentions the marker while recording a real count -- "…the
first line to graduate from [ESTIMATE] to a real count" -- is the OPPOSITE of an
estimate, and a substring test reports it as one. `docs/TRAPS.md` recorded this
before this script was written; the first version of this script used
`icontains` anyway and produced a fourth wrong number about this one field.

A substring match on a marker is not a marker test.

    itq run scripts/estimate_audit.py
    itq run scripts/estimate_audit.py --notes    # print the notes, to judge direction
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part                                      # noqa: E402
from stock.models import StockItem                                # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--notes", action="store_true", help="print each row's note")
a = ap.parse_args()

MARK = "[ESTIMATE]"
marked = StockItem.objects.filter(notes__startswith=MARK)
loose = StockItem.objects.filter(notes__icontains=MARK)

print(f"notes STARTS WITH {MARK}: {marked.count()}      <- the marker test")
print(f"notes CONTAINS   {MARK}: {loose.count()}      <- not a marker test")
print(f"  difference: {loose.count() - marked.count()} row(s) merely MENTION it")
print(f"Part.description starting with it: "
      f"{Part.objects.filter(description__startswith=MARK).count()}")

dated = marked.exclude(stocktake_date__isnull=True).order_by("pk")
print(f"\nmarker AND stocktake_date -- convention says impossible: {dated.count()}")
for si in dated.select_related("part", "location"):
    loc = si.location.name if si.location else "(unlocated)"
    print(f"  #{si.pk:4}  {si.stocktake_date}  {loc:16} "
          f"qty {float(si.quantity):>7.10g}  {si.part.name[:38]}")
    if a.notes:
        print(f"        {' '.join((si.notes or '').split())[:300]}\n")

print(f"\nmarked, no date (correct state): "
      f"{marked.filter(stocktake_date__isnull=True).count()}")
counted = StockItem.objects.exclude(stocktake_date__isnull=True).count()
print(f"rows carrying a stocktake_date: {counted} of {StockItem.objects.count()}"
      f"   -- {dated.count()} of those are stamped but self-described as uncounted")
