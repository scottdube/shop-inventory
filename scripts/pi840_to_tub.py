"""Pi 3 (row 840) is in the Pi / SBC Tub on LRD Cab6-S4 (Scott, 2026-11-04:
"Yes, Pi's in the tub"). The microSD 1229 and NESDR 1230 are NOT moved: not
asked about, not assumed.
    itq run scripts/pi840_to_tub.py [--commit]"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
tub = StockLocation.objects.get(pathstring="LRD/Countertop Wall/Cab6/Cab6-S4/Pi / SBC Tub")
s = StockItem.objects.get(pk=840)
print(s.part.name[:50], "@", s.location.pathstring)
assert s.location.pathstring == "LRD/Receiving" or s.location_id == tub.pk
if "--commit" not in sys.argv:
    raise SystemExit("DRY RUN - add --commit")
if s.location_id != tub.pk:
    s.move(tub, "In the Pi / SBC tub on Cab6-S4 (Scott, 2026-11-04)", u)
print("tub rows:", sorted(StockItem.objects.filter(location=tub).values_list("pk", flat=True)))
print("ALL VERIFIED" if StockItem.objects.get(pk=840).location_id == tub.pk else "NOT VERIFIED")
