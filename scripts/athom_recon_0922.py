"""READ-ONLY recon before executing the athom-tech-new-vendor chain.

Answers, without writing anything:
  1. does a Company for athom.tech exist under any spelling?
  2. does the part / supplier part already exist (duplicate scan)?
  3. what is the PO reference convention and the next generated reference?
  4. where do the room locations sit, and which location holds HA spares?
  5. what category do comparable smart plugs / ESPHome devices live in?
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

print("=" * 70)
print("1. COMPANY -- any athom spelling?")
print("=" * 70)
for c in Company.objects.filter(name__icontains="athom"):
    print(f"  #{c.pk} {c.name!r} supplier={c.is_supplier} active={c.active} {c.website}")
for c in Company.objects.filter(website__icontains="athom"):
    print(f"  (by website) #{c.pk} {c.name!r} {c.website}")
print(f"  total companies: {Company.objects.count()}  "
      f"suppliers: {Company.objects.filter(is_supplier=True).count()}")

print()
print("=" * 70)
print("2. DUPLICATE SCAN -- part / supplier part")
print("=" * 70)
q = (Part.objects.filter(name__icontains="esphome")
     | Part.objects.filter(name__icontains="smart plug")
     | Part.objects.filter(name__icontains="athom")
     | Part.objects.filter(name__icontains="pg03")
     | Part.objects.filter(IPN__icontains="PG03")
     | Part.objects.filter(description__icontains="esphome")).distinct()
for p in q:
    print(f"  #{p.pk} active={p.active} cat={p.category.pathstring if p.category else None}")
    print(f"      {p.name}")
for sp in SupplierPart.objects.filter(SKU__icontains="PG03"):
    print(f"  sp #{sp.pk} {sp.supplier.name} SKU={sp.SKU}")
print(f"  (matches: {q.count()} parts)")

print()
print("=" * 70)
print("3. PO REFERENCE CONVENTION")
print("=" * 70)
print(f"  next generate_reference() -> {PurchaseOrder.generate_reference()}")
for po in PurchaseOrder.objects.order_by("-pk")[:6]:
    print(f"  {po.reference:>10}  ref_int={po.reference_int:<12} "
          f"status={po.status} supplier={po.supplier.name if po.supplier else None}")
    print(f"      supplier_reference={po.supplier_reference!r}")
mx = PurchaseOrder.objects.order_by("-reference_int").first()
print(f"  MAX reference_int: {mx.reference_int} on {mx.reference}")
print(f"  total POs: {PurchaseOrder.objects.count()}")

print()
print("=" * 70)
print("4. LOCATION TREE")
print("=" * 70)
for loc in StockLocation.objects.filter(name__icontains="in service"):
    print(f"  EXISTING in-service: #{loc.pk} {loc.pathstring}")
print("  -- roots --")
for loc in StockLocation.objects.filter(parent__isnull=True).order_by("name"):
    print(f"  root #{loc.pk} {loc.name!r} kids={loc.children.count()}")
sln = StockLocation.objects.filter(name__iexact="SLN", parent__isnull=True).first()
if sln:
    print(f"  -- SLN #{sln.pk} children --")
    for ch in sln.children.all().order_by("name"):
        n = StockItem.objects.filter(location=ch).count()
        print(f"    #{ch.pk:<5} {ch.name:<40} items_here={n} kids={ch.children.count()}")
print("  -- nanoHD / PO-0175 room-location precedent --")
for si in StockItem.objects.filter(part__name__icontains="nanohd")[:10]:
    print(f"    stock #{si.pk} qty={si.quantity} loc="
          f"{si.location.pathstring if si.location else None}")
print("  -- default_location on HA-ish parts --")
for p in (Part.objects.filter(name__icontains="esphome")
          | Part.objects.filter(name__icontains="shelly")
          | Part.objects.filter(name__icontains="nanohd")
          | Part.objects.filter(name__icontains="tasmota")).distinct():
    print(f"    #{p.pk} {p.name[:46]:<46} default_loc="
          f"{p.default_location.pathstring if p.default_location else None}")

print()
print("=" * 70)
print("5. CATEGORY CANDIDATES")
print("=" * 70)
for nm in ("Smart", "Home", "Automation", "Electrical", "Module", "Network", "Power"):
    for c in PartCategory.objects.filter(name__icontains=nm):
        print(f"  #{c.pk:<5} {c.pathstring:<52} parts={c.parts.count()}")
print("  -- roots --")
for c in PartCategory.objects.filter(parent__isnull=True).order_by("name"):
    print(f"  root #{c.pk:<5} {c.name:<30} parts={c.parts.count()} kids={c.children.count()}")
