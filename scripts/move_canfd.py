import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation

si = StockItem.objects.get(pk=791)
mct2 = StockLocation.objects.get(pk=431)
print(f"before: {si.part.name} at {si.location.pathstring}")

si.location = mct2
si.save()
si.refresh_from_db()
print(f"after:  {si.location.pathstring}")
assert si.location_id == 431, "move did not stick"

p = Part.objects.get(pk=1174)
p.default_location = mct2
p.save()
p.refresh_from_db()
print(f"default_location -> {p.default_location.pathstring}")
