"""Delete drawer locations that do not physically exist, 2026-10-04.

Scott: "elec bench only has 5 drawers per side and MB only has 7". So BL-D6,
BR-D6 and MB-D8..D10 are records with no drawer behind them. They came to light
because labels were printed for every child of BL/BR/MB on 2026-10-03.

Refuses to delete a location that holds stock, has children, or is the
default_location of any part -- something pointing at a phantom drawer means
the thing lives somewhere else, and that needs a person, not a cascade.

    itq run scripts/drop_phantom_drawers_1004.py            # dry run
    itq run scripts/drop_phantom_drawers_1004.py --commit
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

KEEP = {"BL": 5, "BR": 5, "Metrology Bench": 7}

doomed, blocked = [], []
for parent_name, n in KEEP.items():
    par = StockLocation.objects.get(name__iexact=parent_name)
    kids = list(par.get_children())
    print(f"{par.pathstring}: {len(kids)} children {sorted(k.name for k in kids)}")
    for k in kids:
        try:
            num = int(k.name.rsplit("-D", 1)[1])
        except (IndexError, ValueError):
            print(f"   ? {k.name} does not parse as <x>-D<n>; left alone")
            continue
        if num <= n:
            continue
        stock = StockItem.objects.filter(location__in=k.get_descendants(include_self=True)).count()
        subs = k.get_children().count()
        homes = list(Part.objects.filter(default_location=k).values_list("pk", "name"))
        why = []
        if stock:
            why.append(f"{stock} stock rows")
        if subs:
            why.append(f"{subs} child locations")
        if homes:
            why.append(f"default_location of {homes}")
        print(f"   {'BLOCKED' if why else 'delete '} #{k.pk} {k.pathstring}"
              f"  desc={k.description!r} meta={k.metadata}" + (f"  -- {', '.join(why)}" if why else ""))
        (blocked if why else doomed).append(k)

if not args.commit:
    print(f"\nDRY RUN -- {len(doomed)} to delete, {len(blocked)} blocked. add --commit")
    sys.exit(0)

for k in doomed:
    pk, path = k.pk, k.pathstring
    k.delete()
    gone = not StockLocation.objects.filter(pk=pk).exists()
    print(f"{'DELETED' if gone else '!! STILL THERE'} #{pk} {path}")
if blocked:
    print(f"left {len(blocked)} blocked: {[k.name for k in blocked]}")
