"""Row 280 (SANXIXING ESP32-S3-WROOM-1 dev board) is in LRD RB-04 with the
voice-assistant kit (Scott, 2026-11-04: "Yes, it's in RB-04"). Its own note
already said it was mounted on that kit's faceplate; it was missed off the
11-02 kit list, so lrd_kits_to_red_bins.py left it in Receiving.
default_location (SLN B3-R6C3, a spare's home) is left alone.
    itq run scripts/voice_esp32_to_rb04.py [--commit]"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
rb = StockLocation.objects.get(pathstring="LRD/Electronics Bench/Red Bins/RB-04")
s = StockItem.objects.get(pk=280)
print(s.part.name, "@", s.location.pathstring, "->", rb.pathstring)
assert s.location.pathstring in ("LRD/Receiving", rb.pathstring)
if "--commit" not in sys.argv:
    raise SystemExit("DRY RUN - add --commit")
if s.location_id != rb.pk:
    s.move(rb, "In RB-04 with the voice-assistant kit, mounted on its faceplate (Scott, 2026-11-04)", u)
s = StockItem.objects.get(pk=280)
print(s.location.pathstring, "| RB-04 rows:", sorted(StockItem.objects.filter(location=rb).values_list("pk", flat=True)))
print("ALL VERIFIED" if s.location_id == rb.pk else "NOT VERIFIED")
