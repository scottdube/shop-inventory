"""PO-0291 was received from the phone 2026-11-08 to the default_location
(F1-R5C7) because the card's location picker was hard to use at phone width;
Scott put the box in the HOT Info Orbs Club Tub (location 863). Move the row,
leave default_location alone (it is the home of a spare, not where a kit lot sits)."""
import os, sys, django
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings"); django.setup()
from django.contrib.auth import get_user_model
from stock.models import StockItem, StockLocation
from plugins.notes_compat import note_append
s = StockItem.objects.get(pk=1298); dest = StockLocation.objects.get(pk=863)
assert s.location_id == 729 and s.quantity == 120, (s.location_id, s.quantity)
user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
s.move(dest, "Moved 2026-11-08: received from the phone to F1-R5C7 by mistake; Scott put the box in the Info Orbs kit tub", user)
s = StockItem.objects.get(pk=1298)
if s.location_id != 863:
    StockItem.objects.filter(pk=1298).update(location=dest); s = StockItem.objects.get(pk=1298)
note_append(s, "2026-11-08: moved F1-R5C7 -> HOT Info Orbs Club Tub (kit lot for the club build; default_location stays F1-R5C7).")
print("stock 1298 now at", s.location.pathstring, "qty", s.quantity, "url http://192.168.50.10:8001/web/stock/item/1298")
