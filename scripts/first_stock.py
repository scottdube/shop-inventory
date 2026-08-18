"""First real stock in the system: the loose electrolytics, counted by hand.

Three values, three bags, one drawer. Separate StockItems because they are
separate parts - the bag is the compartment, so a future count is "pick up bag,
count" rather than a sorting job.

stocktake_date is set because these ARE a physical count, not an inferred
quantity. That is what makes the rolling bin-check work later: the staleness of
a count is only meaningful if the fresh ones are marked.
"""
import argparse, os, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part
from stock.models import StockLocation, StockItem

DRAWER = "A3-R8C4"
COUNTS = [(693, 7), (694, 5), (695, 7)]

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.filter(name=DRAWER).first()
if not loc:
    sys.exit(f"no such location: {DRAWER}")
print(f"location: {loc.pathstring}\n")

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()

for pk, qty in COUNTS:
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"  #{pk}: missing")
        continue
    existing = StockItem.objects.filter(part=p, location=loc).first()
    if existing:
        print(f"  #{pk} {p.name:<42} already has stock here ({existing.quantity:g})")
        continue
    print(f"  #{pk} {p.name:<42} qty {qty}")
    if a.commit:
        si = StockItem.objects.create(
            part=p, location=loc, quantity=qty,
            notes=f"Hand-counted {date.today().isoformat()}. Kept in its own "
                  "bag inside the drawer so a recount needs no sorting.")
        si.stocktake_date = date.today()
        si.stocktake_user = user
        si.save()
        if p.default_location_id != loc.pk:
            p.default_location = loc
            p.save()

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
tot = StockItem.objects.filter(location__name__regex=r"^[AB][1-3]-R").count()
print(f"stock items in the bin wall now: {tot}")
