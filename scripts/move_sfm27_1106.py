"""Move the 3 SFM-27-W buzzers (#1518, stock 1276) F1-R2C7 -> F1-R3C8 (Scott, 2026-11-06).

R2C7 was full with the two buzzer modules (12 + 4); Scott said so after the
put-away was recorded. R3C8 is the empty drawer right under the speaker (R2C8).
Uses StockItem.move() rather than a queryset .update(location=...) so the move
lands in the stock history; default_location follows the part.
Dry run by default.  itq run scripts/move_sfm27_1106.py [--commit]"""
import os, sys
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django; django.setup()
from django.contrib.auth import get_user_model
from part.models import Part
from stock.models import StockItem, StockLocation

SRC, DST = "LRD/Akro Bins/F1/F1-R2C7", "LRD/Akro Bins/F1/F1-R3C8"
src, dst = StockLocation.objects.get(pathstring=SRC), StockLocation.objects.get(pathstring=DST)
s = StockItem.objects.get(pk=1276)
assert s.part_id == 1518 and s.location_id == src.pk and float(s.quantity) == 3, (s.part_id, s.location, s.quantity)
print("DST holds now:", [x.part.name for x in StockItem.objects.filter(location=dst)])
if "--commit" not in sys.argv:
    print("DRY RUN"); sys.exit(0)
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
s.move(dst, "R2C7 full (Scott 2026-11-06); moved under the speaker.", u)
if StockItem.objects.get(pk=1276).location_id != dst.pk:
    StockItem.objects.filter(pk=1276).update(location=dst)
Part.objects.filter(pk=1518).update(default_location=dst)
s, p = StockItem.objects.get(pk=1276), Part.objects.get(pk=1518)
ok = s.location_id == dst.pk and float(s.quantity) == 3 and p.default_location_id == dst.pk
print(f"stock 1276 x{s.quantity:g} @ {s.location.pathstring}; default {p.default_location.pathstring}")
print("VERDICT:", "SUCCESS" if ok else "FAILED")
