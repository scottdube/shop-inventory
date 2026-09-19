"""Read-only probe for the 22:40 sweep on 2026-09-18.

Two orders to import, and this answers the questions that decide HOW before
anything is written:

  1. eBay 06-15193-19595 — NVIDIA T400 4GB GDDR6 low-profile GPU, $118.00
  2. Amazon 113-9362952-1785800 — biaze 8K Mini DP to DP 1.4 adapter, 2-pack,
     $16.99 (Grand Total on the page is $0.00 — gift card)

Prints: the supplier Companies, a duplicate scan across name/description/IPN/SKU
for both items, the SKU convention on existing eBay supplier parts, and the
candidate categories. Writes NOTHING.
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

print("=" * 70)
print("COMPANIES")
for c in Company.objects.filter(is_supplier=True).order_by("pk"):
    print(f"  #{c.pk:3d} {c.name}")

print("=" * 70)
print("eBay SUPPLIER-PART SKU CONVENTION (what goes in SKU for eBay?)")
ebay = Company.objects.filter(name__icontains="ebay").first()
if ebay:
    sps = SupplierPart.objects.filter(supplier=ebay).order_by("-pk")[:10]
    for sp in sps:
        print(f"  sp #{sp.pk} SKU={sp.SKU!r} pack={sp.pack_quantity} "
              f"part=#{sp.part.pk} {sp.part.name[:50]}")
        print(f"       link={sp.link}")
    print(f"  total eBay supplier parts: "
          f"{SupplierPart.objects.filter(supplier=ebay).count()}")
    print("  recent eBay POs:")
    for po in PurchaseOrder.objects.filter(supplier=ebay).order_by("-pk")[:5]:
        print(f"    {po.reference} supplier_ref={po.supplier_reference!r} "
              f"status={po.status} desc={po.description[:50]}")
else:
    print("  !! no eBay company found")

print("=" * 70)
print("DUPE SCAN — NVIDIA T400 / graphics card")
q = (Part.objects.filter(name__icontains="T400")
     | Part.objects.filter(name__icontains="nvidia")
     | Part.objects.filter(name__icontains="graphics")
     | Part.objects.filter(name__icontains="GPU")
     | Part.objects.filter(name__icontains="video card")
     | Part.objects.filter(description__icontains="nvidia")
     | Part.objects.filter(description__icontains="GDDR")).distinct()
for d in q:
    print(f"  #{d.pk} active={d.active} cat={d.category} | {d.name}")
print(f"  ({q.count()} hits)")
print("  supplier parts with item id 398401022842:")
for sp in SupplierPart.objects.filter(SKU__icontains="398401022842"):
    print(f"    sp #{sp.pk} {sp.supplier} {sp.SKU}")

print("=" * 70)
print("DUPE SCAN — Mini DisplayPort to DisplayPort adapter")
q2 = (Part.objects.filter(name__icontains="displayport")
      | Part.objects.filter(name__icontains="mini dp")
      | Part.objects.filter(name__icontains="biaze")
      | Part.objects.filter(description__icontains="displayport")
      | Part.objects.filter(description__icontains="biaze")).distinct()
for d in q2:
    print(f"  #{d.pk} active={d.active} cat={d.category} | {d.name}")
    for sp in d.supplier_parts.all():
        print(f"        sp: {sp.supplier} SKU={sp.SKU} pack={sp.pack_quantity}")
print(f"  ({q2.count()} hits)")

print("=" * 70)
print("CANDIDATE CATEGORIES (cable/video/computer/RF)")
for c in PartCategory.objects.all().order_by("pk"):
    p = c.pathstring.lower()
    if any(k in p for k in ("cable", "video", "hdmi", "display", "computer",
                            "connector", "rf", "network")):
        n = Part.objects.filter(category=c).count()
        print(f"  #{c.pk:3d} {c.pathstring}  ({n} parts)")
