#!/usr/bin/env python3
"""Read-only: every PC817 part and its stock, before earmarking 15 for LRD."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.models import Q  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem  # noqa: E402

for p in Part.objects.filter(Q(name__icontains="817") | Q(description__icontains="817")
                             | Q(name__icontains="optocoupler") | Q(name__icontains="opto-coupler")):
    print(f"part {p.pk} active={p.active}  {p.name[:70]}")
    for s in StockItem.objects.filter(part=p).select_related("location"):
        loc = s.location.pathstring if s.location else "-"
        print(f"    stock {s.pk}  {s.quantity:g} @ {loc}  meta={list((s.metadata or {}).keys())}")
