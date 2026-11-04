"""Pi 3 (840), microSD (1229) and NESDR (1230) are in the Pi / SBC Tub on LRD Cab6-S4 (Scott, 2026-11-04:
"Yes, Pi's in the tub", then "Yes, both" for 1229 and 1230). Re-runnable; rows
already in the tub are skipped.
    itq run scripts/pi_tub_contents.py [--commit]"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
tub = StockLocation.objects.get(pathstring="LRD/Countertop Wall/Cab6/Cab6-S4/Pi / SBC Tub")
ROWS = [840, 1229, 1230]
for pk in ROWS:
    s = StockItem.objects.get(pk=pk)
    print(pk, s.part.name[:50], "@", s.location.pathstring)
    assert s.location.pathstring == "LRD/Receiving" or s.location_id == tub.pk
if "--commit" not in sys.argv:
    raise SystemExit("DRY RUN - add --commit")
for pk in ROWS:
    s = StockItem.objects.get(pk=pk)
    if s.location_id != tub.pk:
        s.move(tub, "In the Pi / SBC tub on Cab6-S4 (Scott, 2026-11-04)", u)
print("tub rows:", sorted(StockItem.objects.filter(location=tub).values_list("pk", flat=True)))
n = StockItem.objects.filter(pk__in=ROWS, location=tub).count()
print("ALL VERIFIED" if n == len(ROWS) else f"NOT VERIFIED {n}/{len(ROWS)}")
