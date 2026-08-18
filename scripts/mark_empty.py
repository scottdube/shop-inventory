"""Mark drawers VERIFIED EMPTY.

Not the same state as 'never looked at', and the difference matters twice: an
empty drawer is available space, and a bin check should not keep flagging it.
There is no StockItem to stamp, so the fact goes on the location itself.
"""
import argparse, os, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockLocation, StockItem

ap = argparse.ArgumentParser()
ap.add_argument("drawers", nargs="+")
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

for name in a.drawers:
    loc = StockLocation.objects.filter(name=name).first()
    if not loc:
        print(f"  {name}: NO SUCH LOCATION")
        continue
    n = StockItem.objects.filter(location=loc).count()
    if n:
        print(f"  {name}: has {n} stock item(s) - NOT marking empty")
        continue
    tag = f"VERIFIED EMPTY {date.today().isoformat()}"
    old = (loc.description or "").strip()
    print(f"  {name}: {tag}" + (f"   (was: {old})" if old else ""))
    if a.commit:
        loc.description = (tag + (f" — previously labelled: {old}" if old else ""))[:250]
        loc.save()

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
