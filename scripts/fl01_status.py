"""Where is every FL-01 (TO-0001) packing-list row now? Read-only.
    itq run scripts/fl01_status.py"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from order.models import TransferOrder
from stock.models import StockItem
to = TransferOrder.objects.get(reference="TO-0001")
print(to.reference, to.get_status_display() if hasattr(to, "get_status_display") else to.status, to.lines.count(), "lines")
for l in to.lines.select_related("part").order_by("part__name"):
    allocs = list(l.allocations.select_related("item"))
    if not allocs:
        print(f"NOALLOC|{l.part.pk}|{l.part.name[:60]}|{float(l.quantity):g}|")
    for a in allocs:
        s = StockItem.objects.filter(pk=a.item_id).first()
        if s is None:
            print(f"GONE|{l.part.pk}|{l.part.name[:60]}|{float(a.quantity):g}|row {a.item_id} deleted")
            continue
        print(f"{s.pk}|{l.part.pk}|{l.part.name[:60]}|{float(s.quantity):g}|{s.location.pathstring if s.location else 'NONE'}")
