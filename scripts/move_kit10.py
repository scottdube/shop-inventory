"""Re-parent the 10-value electrolytic bag into its drawer, A3-R8C5.

The kit stays a location in its own right, now nested inside the drawer: the
drawer is the address, the bag is the container, the ten values live in the bag.
Re-parenting carries the contents, so nothing else has to be touched.
"""
import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockLocation
from part.models import Part

KIT = "Kit - 10-Value Electrolytic 4x7"
DRAWER = "A3-R8C5"

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

kit = StockLocation.objects.filter(name=KIT).first()
drawer = StockLocation.objects.filter(name=DRAWER).first()
if not kit or not drawer:
    sys.exit(f"missing: kit={bool(kit)} drawer={bool(drawer)}")

print(f"  from: {kit.pathstring}")
print(f"  to:   {drawer.pathstring}/{KIT}")
kids = Part.objects.filter(default_location=kit)
print(f"  parts homed in this bag: {kids.count()}")
for p in kids:
    print(f"     #{p.pk} {p.name}")

if a.commit:
    kit.parent = drawer
    kit.description = (f"10value 4x7mm Electrolytic Capacitors, bagged. "
                       f"Lives in drawer {DRAWER}, beside the 5x11/6x12 loose "
                       "stock in A3-R8C4.")[:250]
    kit.save()
    print(f"\n  now: {StockLocation.objects.get(pk=kit.pk).pathstring}")

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
