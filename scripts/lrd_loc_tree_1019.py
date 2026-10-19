"""Read-only: print the LRD stock-location tree with item counts and descriptions.

Run before designing the LRD storage scheme so new locations extend what
exists instead of starting a second convention.
"""
import os, sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockLocation, StockItem  # noqa: E402

roots = StockLocation.objects.filter(name="LRD", parent=None)
if not roots:
    print("no LRD root")
for root in roots:
    for loc in root.get_descendants(include_self=True).order_by("tree_id", "lft"):
        depth = loc.level - root.level
        n = StockItem.objects.filter(location=loc).count()
        desc = (loc.description or "")[:70]
        print(f"{'  ' * depth}{loc.name}  [pk {loc.pk}, {n} items]  {desc}")
