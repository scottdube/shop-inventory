"""READ-ONLY: where does HA / smart-home gear actually live?

The decision item names the spares destination only as "the spares location
which is the one that keeps a default_location" -- it does not name it. This
probe looks for an established home rather than inventing one.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

print("=" * 70)
print("A. The Shelly bin (closest HA sibling) and its neighbours")
print("=" * 70)
bin_ = StockLocation.objects.filter(name="A3-R6C7").first()
if bin_:
    print(f"  #{bin_.pk} {bin_.pathstring}  desc={bin_.description!r}")
    for si in StockItem.objects.filter(location=bin_):
        print(f"    stock #{si.pk} qty={si.quantity:>8} part #{si.part.pk} {si.part.name[:52]}")
    par = bin_.parent
    print(f"  -- siblings under {par.pathstring} --")
    for s in par.children.all().order_by("name"):
        n = StockItem.objects.filter(location=s).count()
        print(f"    #{s.pk:<5} {s.name:<14} items={n:<3} {s.description[:44]!r}")

print()
print("=" * 70)
print("B. Any location whose name/description mentions HA / smart / automation")
print("=" * 70)
for term in ("smart", "home assist", " ha ", "automation", "esphome", "iot", "spare"):
    for loc in (StockLocation.objects.filter(name__icontains=term)
                | StockLocation.objects.filter(description__icontains=term)).distinct():
        n = StockItem.objects.filter(location=loc).count()
        print(f"  [{term:>11}] #{loc.pk:<5} {loc.pathstring:<44} items={n} "
              f"desc={loc.description[:40]!r}")

print()
print("=" * 70)
print("C. Where do comparable smart plugs / HA devices sit RIGHT NOW?")
print("=" * 70)
for pk in (389, 484, 79, 1214):
    p = Part.objects.filter(pk=pk).first()
    if not p:
        continue
    dl = p.default_location.pathstring if p.default_location else None
    print(f"  #{p.pk} {p.name[:54]}")
    print(f"      default_location = {dl}")
    for si in StockItem.objects.filter(part=p):
        print(f"      stock #{si.pk} qty={si.quantity} at "
              f"{si.location.pathstring if si.location else None}")

print()
print("=" * 70)
print("D. Bin Wall shape -- how big is a cell, and is A3 full?")
print("=" * 70)
bw = StockLocation.objects.filter(name="Bin Wall").first()
if bw:
    for a in bw.children.all().order_by("name"):
        kids = a.children.count()
        used = StockItem.objects.filter(location__in=a.children.all()).count()
        print(f"  #{a.pk:<5} {a.name:<8} cells={kids:<4} cells_with_stock={used} "
              f"desc={a.description[:40]!r}")
