"""Count, then split the mmWave sensors between SLN and LRD.

The seeded StockItem said 10 - "quantity as ordered", never counted. A hand
count says 8. So: stocktake to 8 (which logs the correction properly rather
than silently overwriting), then split 5 off to LRD and move the remaining 3
into their drawer.

Using InvenTree's own stocktake/splitStock/move so the history is recorded and
purchase_price rides along to both halves.
"""
import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
si = StockItem.objects.filter(part_id=106).order_by("pk").first()
drawer = StockLocation.objects.get(name="B3-R2C5")
lrd = StockLocation.objects.get(name="LRD")

print(f"before:  qty {si.quantity:g} @ {si.location.pathstring}  price {si.purchase_price}")
print(f"counted: 8   ->  3 stay in {drawer.name}, 5 go to {lrd.name}")

if a.commit:
    si.stocktake(8, user, notes="Hand count 2026-08-17. Seed record said 10 "
                                "(quantity as ordered, never verified); 2 unaccounted.")
    si.refresh_from_db()

    moved = si.splitStock(5, lrd, user,
                          notes="5 of 8 carried to LRD 2026-08-17.")
    si.refresh_from_db()
    si.move(drawer, "3 of 8 stay at SLN, filed to drawer 2026-08-17.", user)

    p = Part.objects.get(pk=106)
    p.default_location = drawer
    p.save()

print()
for x in StockItem.objects.filter(part_id=106).order_by("pk"):
    print(f"  qty {x.quantity:g}  @ {x.location.pathstring if x.location else '-'}"
          f"   price {x.purchase_price}")
print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
