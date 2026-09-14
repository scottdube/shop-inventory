import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from decimal import Decimal
from part.models import Part
from stock.models import StockItem, StockLocation

p = Part.objects.get(pk=1199)
loc = StockLocation.objects.get(pk=587)      # WS2-S4 / Bearings & Motion
assert StockItem.objects.filter(part=p).count() == 0, "already has stock"

si = StockItem.objects.create(
    part=p, location=loc, quantity=Decimal('1'),
    notes=("Counted 1 by Scott 2026-09-14 during the wire-shelf stock-in. A "
           "tallied count, not an estimate.\n\n"
           "Found loose on the wire shelves, uncatalogued. Amazon ASIN "
           "B07ZJ4B272, purchased 2023-06-22 in the 1.2 in / 30 mm size."),
)
si.refresh_from_db()
print(f"stock {si.pk}  qty={float(si.quantity):g}  @ {si.location.pathstring}")

p.default_location = loc
p.save(); p.refresh_from_db()
if p.default_location_id != loc.pk:
    Part.objects.filter(pk=p.pk).update(default_location=loc)
    p.refresh_from_db()
print(f"default_location -> {p.default_location.pathstring}")

# The bin's scope line lists only PASSIVE motion parts. Keep it accurate.
add = ("\n\nPOWERED MOTION LIVES HERE TOO, as of 2026-09-14: the DC HOUSE 12V "
       "mini linear actuator (#1199) is in this bin. The scope line above lists "
       "only passive parts because until now that was all there was. 'Motion' "
       "is the organising idea, not 'unpowered' -- an actuator belongs with the "
       "rails and bushings it would drive, not in an electronics drawer.")
if 'POWERED MOTION' not in (loc.description or ''):
    loc.description = (loc.description or '') + add
    loc.save(); loc.refresh_from_db()
print(f"bin scope note added: {'POWERED MOTION' in loc.description}")
print(f"bin now holds {StockItem.objects.filter(location=loc).count()} rows")
