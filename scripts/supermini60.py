import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem
p = Part.objects.get(pk=60)
print("NAME:", p.name)
print("DESC:", p.description)
for s in StockItem.objects.filter(part=p):
    print(f"  qty={s.quantity:g} avail={s.unallocated_quantity():g} loc={s.location.name if s.location else '-'} price={s.purchase_price}")
print("NOTES:")
print((p.notes or "")[:900])
