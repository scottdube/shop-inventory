"""Read-only: re-read PO-0185/0186 after receive (silent-save check), 2026-10-04."""
import os, sys, django
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings"); django.setup()
from order.models import PurchaseOrder
from stock.models import StockItem
for ref, part in (("PO-0185", 1057), ("PO-0186", 1265)):
    po = PurchaseOrder.objects.get(reference=ref)
    print(ref, "status", po.status, po.complete_date)
    for s in StockItem.objects.filter(part_id=part):
        print("   SI", s.pk, s.quantity, s.location.pathstring, "SN", s.serial, "PO", s.purchase_order_id, "price", s.purchase_price)
