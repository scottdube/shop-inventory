"""Move the 1.44in ST7735 TFT (part 1492, stock 1233) from F1-R2C7 into F0-R1C3.

Scott, 2026-11-04: keep the swap-meet displays together in the large drawer with
the 3.5in Adafruit TFT (part 1499). Displays share a drawer as one kind, like the
diodes. default_location follows, so a returned spare goes to F0-R1C3 too.

    itq run scripts/swap_meet_1027_move_tft144.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
src = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R2C7")
dst = StockLocation.objects.get(pathstring="LRD/Akro Bins/F0/F0-R1C3")
s = StockItem.objects.get(pk=1233)
assert s.part_id == 1492 and s.location_id == src.pk, (s.part_id, s.location)
held = [x.part.name for x in StockItem.objects.filter(location=dst)]
assert all("TFT" in h for h in held), held
print(f"{s.part.name} x{s.quantity:g}: {src.name} -> {dst.name} (holds {held})")
if "--commit" not in sys.argv:
    raise SystemExit("DRY RUN - add --commit")
s.move(dst, "Displays kept together with the 3.5in TFT (Scott, 2026-11-04)", u)
Part.objects.filter(pk=1492).update(default_location=dst)
s, p = StockItem.objects.get(pk=1233), Part.objects.get(pk=1492)
left = StockItem.objects.filter(location=src).count()
print(f"stock {s.pk} @ {s.location.pathstring} x{s.quantity:g} | default {p.default_location.pathstring} | {src.name} rows left {left}")
print("ALL VERIFIED" if s.location_id == dst.pk and p.default_location_id == dst.pk and s.quantity == 1 else "NOT VERIFIED")
