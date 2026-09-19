#!/usr/bin/env python3
"""Search for the Stontronics DSA-13PFC-05 micro-USB supply before creating it."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.models import Q
from part.models import Part
from stock.models import StockItem

TERMS = ["stontronics", "DSA-13PFC", "T5989", "micro-usb", "micro usb", "microusb",
         "5.1V", "5.1 V", "2.5A", "2.5 A", "raspberry", "dee van", "official"]
seen = {}
for t in TERMS:
    qs = Part.objects.filter(Q(name__icontains=t) | Q(description__icontains=t) |
                             Q(keywords__icontains=t))
    for p in qs:
        seen.setdefault(p.pk, set()).add(t)
print(f"{len(seen)} parts matched any term (uncapped, nothing truncated)\n")
for pk in sorted(seen):
    p = Part.objects.get(pk=pk)
    rows = StockItem.objects.filter(part=p)
    loc = ", ".join(f"{r.quantity:g}@{r.location.pathstring if r.location else 'NO LOC'}" for r in rows) or "no stock row"
    print(f"#{p.pk:5d} active={p.active}  {p.name[:72]}")
    print(f"        cat={p.category.pathstring if p.category else '-'}")
    print(f"        {loc}")
    print(f"        hits: {sorted(seen[pk])}")
print("\n--- all parts in Electronics/Power (pk 54) ---")
for p in Part.objects.filter(category__pk=54).order_by("pk"):
    print(f"#{p.pk:5d} active={p.active}  {p.name[:80]}")
