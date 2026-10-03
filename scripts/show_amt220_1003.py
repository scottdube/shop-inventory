"""Read-only: show part 1268 (AMTAST AMT220 roughness tester) with its PO lines and stock."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from order.models import PurchaseOrderLineItem
from stock.models import StockItem

p = Part.objects.get(pk=1268)
print(f"name: {p.name}\ndesc: {p.description}\nkeywords: {p.keywords}\nnotes: {p.notes}\n"
      f"category: {p.category}\ncreated: {getattr(p, 'creation_date', None)}\nlink: {p.link}\n"
      f"metadata: {p.metadata}")
for li in PurchaseOrderLineItem.objects.filter(part__part=p):
    po = li.order
    print(f"PO {po.reference} status={po.get_status_display()} supplier={po.supplier} "
          f"qty={li.quantity} received={li.received} price={li.purchase_price} sku={li.part.SKU} "
          f"target={po.target_date} issued={po.issue_date} supplier_ref={po.supplier_reference}")
for s in StockItem.objects.filter(part=p):
    print(f"stock {s.pk} qty={s.quantity} loc={s.location}")
