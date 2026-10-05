"""Read-only: before adding the BOJACK T3AL250V 3 A 5x20 slow-blow fuses
(Amazon 112-7363556-2703463, 2025-07-27, pack of 20) -- is there already a part,
supplier part, PO or stock row for them, and does a location for the 1100MX
electrical cabinet exist? Searches the requirement (fuse), not only the brand."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.models import Q
from part.models import Part, PartCategory
from company.models import SupplierPart
from order.models import PurchaseOrder, PurchaseOrderLineItem
from stock.models import StockItem, StockLocation

print("== parts matching fuse (all printed, no cap)")
q = Q()
for t in ["fuse", "T3A", "bojack", "5x20", "slow blow", "slow-blow", "time-delay", "time delay"]:
    q |= Q(name__icontains=t) | Q(description__icontains=t) | Q(keywords__icontains=t)
for p in Part.objects.filter(q).distinct():
    print(f"  pk={p.pk} active={p.active} stock={p.total_stock} cat={p.category} "
          f"default_loc={p.default_location} | {p.name} | {p.description[:70]}")

print("== supplier parts matching")
for sp in SupplierPart.objects.filter(Q(SKU__icontains="bojack") | Q(description__icontains="fuse")
                                      | Q(link__icontains="fuse") | Q(SKU__icontains="fuse")).distinct():
    print(f"  sp={sp.pk} part={sp.part_id} {sp.supplier} SKU={sp.SKU} pack={sp.pack_quantity} | {sp.description[:70]}")

print("== POs carrying the order number")
for po in PurchaseOrder.objects.filter(Q(supplier_reference__icontains="7363556")
                                       | Q(reference__icontains="7363556")
                                       | Q(description__icontains="7363556")
                                       | Q(notes__icontains="7363556")):
    print(f"  {po.reference} status={po.status} supplier={po.supplier} sref={po.supplier_reference}")
    for li in po.lines.all():
        print(f"    line {li.pk} part={li.part} qty={li.quantity} recv={li.received}")
for li in PurchaseOrderLineItem.objects.filter(Q(notes__icontains="fuse") | Q(reference__icontains="fuse")
                                              | Q(part__SKU__icontains="bojack")):
    print(f"  line {li.pk} on {li.order.reference} part={li.part}")

print("== locations: 1100 / tormach / cabinet / electrical (all printed)")
lq = Q()
for t in ["1100", "tormach", "cabinet", "electrical"]:
    lq |= Q(name__icontains=t) | Q(description__icontains=t)
for loc in StockLocation.objects.filter(lq).distinct():
    print(f"  loc={loc.pk} path={loc.pathstring} | {loc.description[:60]} | items={loc.stock_items.count()}")

print("== categories with fuse / protection / circuit")
for c in PartCategory.objects.filter(Q(name__icontains="fuse") | Q(name__icontains="protect")
                                     | Q(name__icontains="circuit")):
    print(f"  cat={c.pk} path={c.pathstring} parts={c.parts.count()}")
