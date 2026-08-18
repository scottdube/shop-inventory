import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem

for pk in [int(x) for x in sys.argv[1:]]:
    p = Part.objects.get(pk=pk)
    print(f"#{p.pk} {p.name}")
    for si in StockItem.objects.filter(part=p):
        loc = si.location.pathstring if si.location else "NO LOCATION"
        print(f"   qty {si.quantity:g}  @ {loc}")
        print(f"      price={si.purchase_price}  stocktake={si.stocktake_date}")
        if si.notes:
            print(f"      notes: {si.notes[:90]}")
    print()
