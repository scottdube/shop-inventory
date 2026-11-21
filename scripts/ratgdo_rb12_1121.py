"""Read-only: list every stock row in SLN RB-12 and how many RB-12 locations exist."""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockItem, StockLocation  # noqa: E402

locs = StockLocation.objects.filter(name="RB-12")
for l in locs:
    print(f"LOCATION pk={l.pk} {l.pathstring}")
sln = [l for l in locs if l.pathstring.startswith("SLN/")][0]
for s in StockItem.objects.filter(location=sln).select_related("part"):
    print(f"  stock pk={s.pk} part={s.part.pk} qty={float(s.quantity):g} {s.part.name[:70]} md={s.metadata or ''}")
for pk in (243, 325):
    s = StockItem.objects.get(pk=pk)
    print(f"OTHER stock pk={s.pk} part={s.part.pk} qty={float(s.quantity):g} {s.part.name[:60]} @ {s.location.pathstring} md={s.metadata or ''}")
