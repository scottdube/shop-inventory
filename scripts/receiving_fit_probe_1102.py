#!/usr/bin/env python3
"""Read-only: every row in LRD/Receiving with the SLN home its part (or its
commute marker) points at, so the Akro fill can follow how SLN stored it.
Also prints the F0/F1/F2 grid and the SLN Akro cabinets' descriptions."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from collections import Counter  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

rec = StockLocation.objects.get(pathstring="LRD/Receiving")
for s in StockItem.objects.filter(location=rec).select_related("part", "part__category",
                                                               "part__default_location"):
    m = (s.metadata or {}).get("commutes")
    home = m["home_path"] if m else (s.part.default_location.pathstring
                                     if s.part.default_location else "-")
    cat = s.part.category.name if s.part.category else "-"
    print(f"{s.pk:5}|{s.quantity:g}|{'C' if m else ' '}|{home}|{cat}|{s.part.name[:70]}")

print()
for f in ("F0", "F1", "F2"):
    loc = StockLocation.objects.get(pathstring=f"LRD/Akro Bins/{f}")
    kids = list(loc.get_children().order_by("name").values_list("name", flat=True))
    rows = Counter(k.split("-")[1].split("C")[0] for k in kids)
    print(f"{f}: {len(kids)} cells, rows {dict(rows)}  first {kids[:1]} last {kids[-1:]}")
    print(f"    {(loc.description or '')[:200]}")

for l in StockLocation.objects.filter(pathstring__regex=r"^SLN/.*/A[0-9]$"):
    print(f"{l.pathstring}: {(l.description or '')[:200]}")
