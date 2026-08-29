"""What cable and adapter parts exist, and where are they? Read-only.

Sizing input for a cable-storage plan: Scott 2026-08-28 expects "a lot of cable
adapters" and wants capacity for the current population plus 50%.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.models import Q
from part.models import Part, PartCategory
from stock.models import StockItem

CABLE = (Q(name__icontains="cable")|Q(name__icontains="adapter")|Q(name__icontains="cord")
         |Q(name__icontains="lead")|Q(name__icontains="jumper")|Q(name__icontains="patch")
         |Q(name__icontains="extension")|Q(name__icontains="pigtail")
         |Q(name__icontains="dongle")|Q(name__icontains="converter"))
parts = Part.objects.filter(CABLE, active=True)
print(f"active cable/adapter-ish parts: {parts.count()}")
stocked = [p for p in parts if p.total_stock]
print(f"  with stock: {len(stocked)}   without: {parts.count()-len(stocked)}")

print("\n== by category ==")
cats = {}
for p in parts:
    cats.setdefault(str(p.category), []).append(p)
for c, v in sorted(cats.items(), key=lambda x: -len(x[1]))[:8]:
    print(f"  {len(v):>3}  {c[:56]}")

print("\n== where the stocked ones live ==")
locs = {}
for p in stocked:
    for s in StockItem.objects.filter(part=p):
        locs.setdefault(s.location.name if s.location else "(none)", 0)
        locs[str(s.location.name if s.location else '(none)')] += 1
for l, n in sorted(locs.items(), key=lambda x: -x[1]):
    print(f"  {n:>3}  {l}")

print("\n== the stocked ones, by name ==")
for p in sorted(stocked, key=lambda x: x.name):
    s = StockItem.objects.filter(part=p).first()
    print(f"  #{p.pk:4} {p.name[:54]:56} {float(p.total_stock):>4g} "
          f"{s.location.name if s and s.location else '-'}")
