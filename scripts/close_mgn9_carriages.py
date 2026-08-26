"""Close the open carriage count on the MGN9 rails: 2 total, one per rail.

Scott 2026-08-26. The dark piece visible in the white bag was not a third
block. Two rails, two carriages, nothing loose -- so the rail row is complete
as it stands and no separate carriage part is needed.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part
from stock.models import StockItem

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
p = Part.objects.get(pk=1117)
si = StockItem.objects.filter(part=p).first()
print(f"{p.name}\n  stock [{si.pk}] qty={si.quantity:g} stocktake_date={si.stocktake_date}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

si.stocktake(2, user, notes="Counted in hand by Scott 2026-08-26: 2 rails, 2 carriages.")
StockItem.objects.filter(pk=si.pk).update(notes=(
    "TALLIED 2026-08-26. Two rails, each with ONE carriage. Two carriages "
    "total -- Scott confirmed, and the dark piece visible in the white bag was "
    "not a third block.\n\n"
    "No separate carriage part exists and none is needed: the count is 1:1 with "
    "the rails, so the rail row carries it. Create one only if loose blocks "
    "ever arrive on their own.\n\n"
    "Block type MGN9C (short) vs MGN9H (long) is still unrecorded -- they "
    "differ in load rating and mounting-hole spacing."))

# The part-level note still says the total is uncounted. Fix it there too, or
# the closed question stays open everywhere anyone actually reads.
Part.objects.filter(pk=p.pk).update(notes=(p.notes or "").replace(
    "BLOCK TYPE NOT CONFIRMED",
    "CARRIAGES: 2, one per rail, counted by Scott 2026-08-26.\n\n"
    "BLOCK TYPE NOT CONFIRMED"))

si.refresh_from_db()
print(f"  after: qty={si.quantity:g} stocktake_date={si.stocktake_date}")
