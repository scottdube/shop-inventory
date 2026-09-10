import os, sys, django, datetime
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from decimal import Decimal
from part.models import Part
from stock.models import StockItem, StockLocation

p = Part.objects.get(pk=1184)
loc = StockLocation.objects.get(pk=431)          # SLN/Mobile Cart/MC-T2

assert StockItem.objects.filter(part=p).count() == 0, "already has stock -- stop"

si = StockItem.objects.create(
    part=p, location=loc, quantity=Decimal('1'),
    purchase_price=Decimal('179.99'), purchase_price_currency='USD',
    notes=("Amazon order 113-1305022-6114620, delivered 2026-05-25, sold by "
           "MaguireStore. $179.99 list; $136.27 actually paid after $56.32 of "
           "rewards points -- the 179.99 is recorded as the price because that "
           "is what the instrument is worth, not what the points made it cost.\n\n"
           "MAY GO TO FLORIDA FOR THE WINTER -- Scott, 2026-09-10. Earmarked, "
           "NOT decided. It stays in MC-T2 and stays usable until someone packs it."),
)
si.refresh_from_db()
print(f"stock {si.pk}  qty={si.quantity}  at {si.location.pathstring}")

p.default_location = loc
p.save()
p.refresh_from_db()
print(f"default_location -> {p.default_location.pathstring}")

# drawer description was already stale: it lists 3 items and holds 4.
loc.description = (
    "Test gear. Nordic Power Profiler Kit II (PPK2) -- source-meter / uA current "
    "profiler, and the most valuable thing in this drawer. Lonely Binary 8ch "
    "24MHz logic analyzer kit and the Digilent OpenScope MZ. GME 236 in-circuit "
    "ESR/DCR capacitor tester with hook-clip test leads. FNIRSI LCR-P1 component "
    "tester. Updated 2026-09-10 -- it had listed three of the four things already "
    "in it."
)
loc.save()
loc.refresh_from_db()
ok = 'PPK2' in loc.description and 'FNIRSI' in loc.description
print(f"MC-T2 description updated: {ok}")
