"""Stock the Walmart Sterilite 6qt bin 10-pack (#1089) into SLN/Receiving.

Receiving, not a shelf: they have arrived but have no home yet, and one is
about to become a LOCATION rather than stock. A bin in use stops being
inventory and starts being a place.
"""
import argparse, datetime, os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part                       # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

p = Part.objects.get(pk=1089)
loc = StockLocation.objects.get(name="Receiving", parent__name__startswith="SLN")
print(f"#{p.pk} {p.name}")
print(f"  existing stock: {p.stock_items.count()}")
print(f"  -> 10 @ {loc.pathstring}")
if p.stock_items.exists():
    print("!! already stocked — refusing"); raise SystemExit(1)
if not a.commit:
    print("\nDRY RUN"); raise SystemExit

si = StockItem.objects.create(
    part=p, location=loc, quantity=10,
    stocktake_date=datetime.date(2026, 8, 24),
    notes=("Walmart 10-pack, arrived and confirmed on hand by Scott 2026-08-24. "
           "Counted as 10 unopened from the pack he has in front of him. NOTE: "
           "as each bin goes into service it becomes a LOCATION, not stock — "
           "decrement this row when one is put to work."))
c = StockItem.objects.get(pk=si.pk)
assert float(c.quantity) == 10 and c.location_id == loc.pk
print(f"OK  stock #{c.pk} qty=10 @ {c.location.name}")
