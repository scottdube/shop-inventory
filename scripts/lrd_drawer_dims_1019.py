"""Record Scott's measured drawer sizes on the three LRD drawer banks.

Scott, 2026-10-19: top 2 drawers 24 1/4 x 18 1/2 x 2 1/4 in; lower 3 same
footprint x 6 in. Width/depth read against the 28 x 22.5 in exterior (26.5 in
inside). The three banks are one order line (GC-8103 Base 5 Drawer x3), so one
bank measured covers all three.

Dry run by default; --commit writes and re-reads.
"""
import os, sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
BANKS = {530: "Cab2", 531: "Cab3", 532: "Cab4"}
OLD = "5 drawers per the installer render and 2026-10-19 photos; confirm against the prints before building"
NEW = ("5 drawers. D1-D2 (top two) 24.25 W x 18.5 D x 2.25 H in; D3-D5 24.25 W x 18.5 D x "
       "6 H in (Scott measured 2026-10-19; one bank measured, all three are the same order "
       "line). Drawers will be")

plans = []
for pk, name in BANKS.items():
    loc = StockLocation.objects.get(pk=pk)
    assert loc.name == name, (pk, loc.name)
    assert loc.description.count(OLD) == 1, (name, loc.description)
    plans.append((loc, loc.description.replace(OLD, NEW)))
    print(f"{'WRITE' if COMMIT else 'would'} {name}")

if COMMIT:
    for loc, d in plans:
        loc.description = d
        loc.save()
    bad = 0
    for loc, d in plans:
        ok = StockLocation.objects.get(pk=loc.pk).description == d
        bad += not ok
        print(f"  {'OK ' if ok else 'BAD'} {loc.name}")
    print("ALL VERIFIED" if not bad else f"{bad} NOT WRITTEN")
else:
    print(plans[0][1])
