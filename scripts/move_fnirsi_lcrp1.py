"""Move the FNIRSI LCR-P1 (part 1056, stock 572) from LRD/Receiving into Cab4-D4.

Scott, 2026-11-04: it is physically in Cab4-D4 with the other test gear (the TC1,
part 1500). Receiving is a staging area, never a home, so default_location
moves to Cab4-D4 as well.

    itq run scripts/move_fnirsi_lcrp1.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
src = StockLocation.objects.get(pathstring="LRD/Receiving")
dst = StockLocation.objects.get(pathstring="LRD/Countertop Wall/Cab4/Cab4-D4")
s = StockItem.objects.get(pk=572)
assert s.part_id == 1056 and s.location_id == src.pk, (s.part_id, s.location)
held = [x.part.name for x in StockItem.objects.filter(location=dst)]
assert all("Tester" in h for h in held), held
print(f"{s.part.name} x{s.quantity:g}: {src.name} -> {dst.name} (holds {held})")
if "--commit" not in sys.argv:
    raise SystemExit("DRY RUN - add --commit")
s.move(dst, "Out of Receiving; test gear lives in Cab4-D4 for now (Scott, 2026-11-04)", u)
Part.objects.filter(pk=1056).update(default_location=dst)
s, p = StockItem.objects.get(pk=572), Part.objects.get(pk=1056)
print(f"stock {s.pk} @ {s.location.pathstring} x{s.quantity:g} | default {p.default_location.pathstring}")
print("ALL VERIFIED" if s.location_id == dst.pk and p.default_location_id == dst.pk and s.quantity == 1 else "NOT VERIFIED")
