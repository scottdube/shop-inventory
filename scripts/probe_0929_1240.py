"""Read-only probe, 12:40 sweep 2026-09-29, before importing two orders.

  Amazon 113-9034798-2737037  Brother QL-810W (Renewed)  B07MDHL97G  $129.99
  Haas   1000520353           03-3399 1/2" keyseat cutter, 10 fl   $89.95 less $9.00

Questions: does part #1057 (the existing QL-810W) already carry this ASIN, and
how is it serialised; is 03-3399 / a keyseat cutter already a part; how did the
last Haas POs book an order discount.
"""
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem  # noqa: E402

print("=== QL-810W")
for p in Part.objects.filter(Q(name__icontains="QL-810") | Q(name__icontains="QL810")
                             | Q(description__icontains="QL-810") | Q(keywords__icontains="QL-810")):
    print(f"part #{p.pk} active={p.active} trackable={p.trackable} {p.name!r} "
          f"cat={p.category.pathstring if p.category else None} IPN={p.IPN!r}")
    for sp in p.supplier_parts.all():
        print(f"   sp #{sp.pk} {sp.supplier.name} SKU={sp.SKU} pack={sp.pack_quantity}")
    for si in StockItem.objects.filter(part=p):
        print(f"   stock #{si.pk} serial={si.serial!r} qty={si.quantity} "
              f"loc={si.location} status={si.status}")
for sp in SupplierPart.objects.filter(SKU__iexact="B07MDHL97G"):
    print(f"ASIN already on sp #{sp.pk} part #{sp.part_id}")
for po in PurchaseOrder.objects.filter(lines__part__part__name__icontains="QL-810").distinct():
    print(f"   {po.reference} {po.supplier_reference} status={po.status} {po.description[:80]!r}")

print("\n=== keyseat / 03-3399")
for p in Part.objects.filter(Q(name__icontains="keyseat") | Q(description__icontains="keyseat")
                             | Q(name__icontains="woodruff") | Q(IPN__iexact="03-3399")
                             | Q(description__icontains="03-3399")):
    print(f"part #{p.pk} active={p.active} {p.name!r} IPN={p.IPN!r} "
          f"cat={p.category.pathstring if p.category else None}")
for sp in SupplierPart.objects.filter(SKU__iexact="03-3399"):
    print(f"SKU already on sp #{sp.pk} part #{sp.part_id}")

print("\n=== Haas companies and recent POs")
for c in Company.objects.filter(name__icontains="haas"):
    print(f"company #{c.pk} {c.name!r} supplier={c.is_supplier}")
    for po in PurchaseOrder.objects.filter(supplier=c).order_by("-pk")[:4]:
        print(f"  {po.reference} {po.supplier_reference} status={po.status}")
        print("    notes:", (po.notes or "")[:600].replace("\n", " | "))
        for li in po.lines.all():
            print(f"    line {li.part.SKU} {li.part.part.name[:60]!r} (#{li.part.part_id}) "
                  f"qty {li.quantity} @ {li.purchase_price}  cat="
                  f"{li.part.part.category.pathstring if li.part.part.category else None}")
            if li.notes:
                print("      line notes:", li.notes[:300].replace("\n", " | "))
        for x in po.extra_lines.all():
            print(f"    extra {x.reference!r} qty {x.quantity} @ {x.price} {x.notes[:100]!r}")
