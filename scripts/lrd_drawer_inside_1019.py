"""Mark the LRD drawer sizes as INSIDE dimensions (Scott, 2026-10-19).

Dry run by default; --commit writes and re-reads.
"""
import os, sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
OLD = "6 H in (Scott measured 2026-10-19;"
NEW = "6 H in, all INSIDE dimensions (Scott measured 2026-10-19;"
plans = []
for pk, name in {530: "Cab2", 531: "Cab3", 532: "Cab4"}.items():
    loc = StockLocation.objects.get(pk=pk)
    assert loc.name == name and loc.description.count(OLD) == 1, (pk, loc.name)
    plans.append((loc, loc.description.replace(OLD, NEW)))
    print(f"{'WRITE' if COMMIT else 'would'} {name}")
if COMMIT:
    for loc, d in plans:
        loc.description = d
        loc.save()
    bad = sum(StockLocation.objects.get(pk=l.pk).description != d for l, d in plans)
    print("ALL VERIFIED" if not bad else f"{bad} NOT WRITTEN")
