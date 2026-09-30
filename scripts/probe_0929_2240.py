"""Read-only probe, 22:40 sweep 2026-09-29, before importing one order.

  Amazon 113-1489119-5361851  PNY NVIDIA T400  sold by Computer Nation Store  $218.00

Questions: is there already a T400 part (the eBay order 06-15193-19595 = PO-0176
was for the same GPU and was CANCELED by the seller today, refund $118.00);
what does PO-0176 look like; is any Amazon supplier part already on the T400.
"""
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem  # noqa: E402

print("=== T400 parts")
for p in Part.objects.filter(Q(name__icontains="T400") | Q(description__icontains="T400")
                             | Q(keywords__icontains="T400")):
    print(f"part #{p.pk} active={p.active} trackable={p.trackable} {p.name!r} "
          f"cat={p.category.pathstring if p.category else None} IPN={p.IPN!r}")
    print(f"   desc={p.description[:200]!r}")
    print(f"   kw={p.keywords!r}")
    for sp in p.supplier_parts.all():
        print(f"   sp #{sp.pk} {sp.supplier.name} SKU={sp.SKU} pack={sp.pack_quantity} "
              f"link={sp.link!r}")
    for si in StockItem.objects.filter(part=p):
        print(f"   stock #{si.pk} qty={si.quantity} loc={si.location} status={si.status}")

print("\n=== PO-0176")
po = PurchaseOrder.objects.get(reference="PO-0176")
print(f"{po.reference} supplier={po.supplier.name} sref={po.supplier_reference} "
      f"status={po.status} target={po.target_date}")
print("   desc:", po.description)
print("   notes:", (po.notes or "")[:900].replace("\n", " | "))
for li in po.lines.all():
    print(f"   line sp #{li.part_id} {li.part.SKU} -> part #{li.part.part_id} "
          f"qty {li.quantity} @ {li.purchase_price} received={li.received}")

print("\n=== Amazon order already on any PO?")
for po in PurchaseOrder.objects.filter(Q(supplier_reference__icontains="113-1489119")
                                       | Q(notes__icontains="113-1489119")):
    print(f"   {po.reference} {po.supplier_reference}")
for sp in SupplierPart.objects.filter(Q(description__icontains="T400") | Q(SKU__icontains="T400")):
    print(f"   sp #{sp.pk} {sp.supplier.name} SKU={sp.SKU} part #{sp.part_id}")
