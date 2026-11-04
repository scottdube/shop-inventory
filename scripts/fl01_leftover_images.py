"""FL-01 rows still in LRD/Receiving + everything else there; copy part images to /tmp/fl01img. Read-only."""
import os, sys, shutil, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockItem, StockLocation
from order.models import TransferOrder
rcv = StockLocation.objects.get(pathstring="LRD/Receiving")
fl = set(TransferOrder.objects.get(reference="TO-0001").lines.values_list("allocations__item", flat=True))
os.makedirs("/tmp/fl01img", exist_ok=True)
for s in StockItem.objects.filter(location=rcv).select_related("part").order_by("part__name"):
    p = s.part
    img = ""
    if p.image:
        img = f"/tmp/fl01img/{s.pk}{os.path.splitext(p.image.name)[1]}"
        shutil.copy(p.image.path, img)
    ann = [n.title for n in s.notes.all()]
    dl = p.default_location.pathstring if p.default_location else "-"
    print(f"{'FL01' if s.pk in fl else 'other'}|{s.pk}|{p.pk}|{p.name[:60]}|{float(s.quantity):g}|{p.category.pathstring if p.category else ''}|{dl}|{ann}|{img}")
