"""Where did the 7 GC9A01s come from, and is there a recent AliExpress display order?"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem
from order.models import PurchaseOrder, PurchaseOrderLineItem

p = Part.objects.get(pk=418)
print(f"#418 {p.name}")
print(f"   desc: {p.description}")
for s in StockItem.objects.filter(part=p):
    po = s.purchase_order.reference if s.purchase_order else "-"
    print(f"   stock {s.pk}: qty={s.quantity:g} @ {s.location.name if s.location else '-'} "
          f"created={s.creation_date} PO={po} price={s.purchase_price}")

print("\nrecent POs mentioning a display or header:")
for line in PurchaseOrderLineItem.objects.filter(part__part__name__iregex=r'GC9A01|round.*lcd|header|socket').order_by("-pk")[:10]:
    o = line.order
    print(f"   {o.reference:10} {str(o.supplier)[:18]:18} {o.creation_date}  {line.part.part.name[:44]:44} qty={line.quantity:g} recv={line.received:g}")

print("\nany 1x7 / 7-pin female header part?")
for q in Part.objects.filter(name__iregex=r'1x7|7-pin|7 pin').filter(active=True):
    tot = sum(s.quantity for s in StockItem.objects.filter(part=q))
    print(f"   #{q.pk} {q.name[:50]}  qty={tot:g}")
