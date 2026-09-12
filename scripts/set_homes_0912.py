import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from part.models import Part
from stock.models import StockLocation, StockItem

for part_pk, loc_pk in ((1186, 563), (1180, 565)):
    p = Part.objects.get(pk=part_pk)
    l = StockLocation.objects.get(pk=loc_pk)
    p.default_location = l
    p.save()
    p.refresh_from_db()
    if p.default_location_id != loc_pk:
        Part.objects.filter(pk=part_pk).update(default_location=l)
        p.refresh_from_db()
    print(f"#{p.pk} {p.name[:50]:50s} home -> {p.default_location.pathstring}")
    for si in StockItem.objects.filter(part=p):
        print(f"        stock {si.pk} qty={float(si.quantity):g} @ {si.location.pathstring}  "
              f"unit=${float(si.purchase_price.amount) if si.purchase_price else 0:.4f}")
