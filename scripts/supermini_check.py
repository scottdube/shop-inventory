"""What ESP32 boards are actually on the shelf, and what is BO-0016 holding?"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem

for pk in (60, 62, 58):
    p = Part.objects.filter(pk=pk).first()
    if not p:
        continue
    print(f"\n#{p.pk} {p.name}")
    print(f"   desc: {(p.description or '')[:110]}")
    for s in StockItem.objects.filter(part=p):
        loc = s.location.name if s.location else "-"
        print(f"   qty={s.quantity:g} avail={s.unallocated_quantity():g} @ {loc}  price={s.purchase_price}")
    if p.notes:
        print(f"   notes: {p.notes[:200]}")
