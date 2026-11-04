"""Move LRD test gear out of LRD/Receiving into Cab4-D4.

Scott, 2026-11-04: "any test equip that came down is there". Two rows qualify:
PPK2 (part 1184) and the Thermal Master P2 Pro (part 1326). Rows under
Equipment/Test Equipment that are NOT test gear stay put: both label
printers (the QL-810W is the working LRD printer), the Einstar 3D scanner, and
the bench PSU, which is recorded on the Countertop Wall rather than in Receiving.
default_location follows each move (Receiving is staging, never a home).

    itq run scripts/move_test_gear_cab4d4.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

ROWS = [(797, 1184), (897, 1326)]  # (stock pk, part pk)
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
src = StockLocation.objects.get(pathstring="LRD/Receiving")
dst = StockLocation.objects.get(pathstring="LRD/Countertop Wall/Cab4/Cab4-D4")
for spk, ppk in ROWS:
    s = StockItem.objects.get(pk=spk)
    assert s.part_id == ppk and s.location_id == src.pk, (spk, s.part_id, s.location)
    print(f"{s.part.name[:55]} x{s.quantity:g}: Receiving -> Cab4-D4")
if "--commit" not in sys.argv:
    raise SystemExit("DRY RUN - add --commit")
bad = []
for spk, ppk in ROWS:
    StockItem.objects.get(pk=spk).move(dst, "Test gear lives in Cab4-D4 for now (Scott, 2026-11-04)", u)
    Part.objects.filter(pk=ppk).update(default_location=dst)
    s, p = StockItem.objects.get(pk=spk), Part.objects.get(pk=ppk)
    print(f"stock {spk} @ {s.location.pathstring} x{s.quantity:g} | default {p.default_location.pathstring}")
    if s.location_id != dst.pk or p.default_location_id != dst.pk:
        bad.append(spk)
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
