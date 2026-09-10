"""Candidate parts for the corrected BO-0016 BOM."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem
def show(label, qs):
    print(f"\n=== {label} ===")
    n=0
    for p in qs:
        if not p.active: continue
        q = sum(s.quantity for s in StockItem.objects.filter(part=p))
        f = sum(s.unallocated_quantity() for s in StockItem.objects.filter(part=p))
        loc = ", ".join(sorted({s.location.name for s in StockItem.objects.filter(part=p) if s.location}))
        print(f"   #{p.pk:5} {p.name[:52]:52} qty={q:g} free={f:g} @ {loc[:22]}")
        n+=1
    if not n: print("   (none)")
show("tactile / push switches", Part.objects.filter(name__iregex=r'tactile|push').order_by("pk"))
show("220uF capacitors", Part.objects.filter(name__icontains="220").filter(name__iregex=r'uf|cap').order_by("pk"))
show("female headers / sockets 1x7-ish", Part.objects.filter(name__iregex=r'female header|socket|1x7|header').order_by("pk")[:12])
show("PCB parts", Part.objects.filter(name__iregex=r'\bPCB\b').order_by("pk")[:8])
show("GC9A01 displays", Part.objects.filter(name__icontains="GC9A01").order_by("pk"))
