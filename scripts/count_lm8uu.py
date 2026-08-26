"""Stocktake the LM8UU bushings: 10 counted, against a label that said 12.

Scott counted 2026-08-26. The bag had been opened -- which is exactly the case
the [ESTIMATE] marker was hedging, and the first time on this install that a
card-stated pack figure has been falsified by an actual count.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from stock.models import StockItem

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
si = StockItem.objects.get(pk=699)
print(f"before: qty={si.quantity:g} stocktake_date={si.stocktake_date}")

if not a.commit:
    print("would set 10, TALLIED\nDRY RUN -- add --commit")
    sys.exit()

si.stocktake(10, user, notes="Counted in hand by Scott 2026-08-26.")
si.refresh_from_db()
StockItem.objects.filter(pk=si.pk).update(notes=(
    "TALLIED 2026-08-26. Scott counted 10 in hand.\n\n"
    "THE BAG LABEL SAID 12. It reads 'BearingLM8UU-12 Pcs-F' and the bag had "
    "been opened, so two were already used. The quantity was held as "
    "card-stated [ESTIMATE] with a null stocktake_date for exactly this reason "
    "and the count falsified it -- the first time on this install that a pack "
    "figure has actually been caught wrong.\n\n"
    "Read that as evidence about the TIER, not about this bag: a printed pack "
    "count on an opened bag is not a count, and 'the label says so' would have "
    "put a wrong number on the shelf permanently."))

si.refresh_from_db()
print(f"after : qty={si.quantity:g} stocktake_date={si.stocktake_date}")
