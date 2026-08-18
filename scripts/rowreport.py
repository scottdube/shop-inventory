import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockLocation, StockItem

prefix = sys.argv[1]
locs = sorted(StockLocation.objects.filter(name__startswith=prefix),
              key=lambda l: int(l.name.rsplit("C", 1)[1]))
tot_items = tot_qty = 0
for loc in locs:
    items = StockItem.objects.filter(location=loc).select_related("part")
    if not items:
        print(f"  {loc.name}   {(loc.description or 'no record')[:56]}")
        continue
    print(f"  {loc.name}")
    for si in items:
        est = "EST" if "ESTIMATE" in (si.notes or "") else "   "
        print(f"        {si.quantity:>5g} {est}  {si.part.name[:58]}")
        tot_items += 1
        tot_qty += si.quantity
print(f"\n  {tot_items} stock items, {tot_qty:g} pieces across {len(locs)} drawers")
