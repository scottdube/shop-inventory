"""Read-only: PO-0182 before booking it for return, 2026-10-04."""
import os, sys, django
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings"); django.setup()
from order.models import PurchaseOrder
from stock.models import StockItem
po = PurchaseOrder.objects.get(reference="PO-0182")
print(po.reference, "status", po.status, po.supplier.name, po.supplier_reference, po.target_date, "total", po.total_price)
print("  desc:", po.description); print("  notes:", (po.notes or "")[-400:])
for l in po.lines.all():
    sp = l.part; p = sp.part
    print(f"  line {l.pk} {sp.SKU} qty {float(l.quantity)} recv {float(l.received)} {l.purchase_price} -> part #{p.pk} {p.name!r} active={p.active}")
    for s in StockItem.objects.filter(part=p):
        print(f"     SI #{s.pk} qty {s.quantity} status {s.status} @ {s.location.pathstring if s.location else None} PO {s.purchase_order_id}")
