#!/usr/bin/env python3
"""Read-only: which build order (project kit) each LRD/Receiving row belongs to,
by build allocation or by appearing in an open build's BOM. Decides RB (one
project per red bin, as at SLN) vs Akro (generic stock by kind)."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from build.models import Build, BuildItem  # noqa: E402
from part.models import BomItem  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

rec = StockLocation.objects.get(pathstring="LRD/Receiving")
open_builds = Build.objects.exclude(status__in=[40, 30])  # not complete/cancelled
print("open builds:")
for b in open_builds.order_by("reference"):
    print(f"  {b.reference} status={b.status} {b.part.name[:50]} | {(b.title or '')[:60]}")
print()
for s in StockItem.objects.filter(location=rec).select_related("part"):
    alloc = sorted({bi.build_line.build.reference for bi in BuildItem.objects.filter(stock_item=s)
                    .select_related("build_line__build")})
    bom = sorted({b.reference for b in open_builds
                  if BomItem.objects.filter(part=b.part, sub_part=s.part).exists()})
    tags = alloc or bom
    print(f"{s.pk:5} {'alloc' if alloc else ('bom' if bom else '-'):5} "
          f"{','.join(tags) or '':22} {s.part.name[:60]}")
