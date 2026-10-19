"""Record the measured shelf count and size on the four LRD upper cabinets.

Scott, 2026-10-19: 16 adjustable/removable shelves across the four uppers plus
each cabinet's floor; shelf 14 x 26.5 in. That is 4 per cabinet, matching order
GC-8103, and settles the "photos show 3" question in favor of the order.

Dry run by default; --commit writes and re-reads.
"""
import os, sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
UPPERS = {525: "Cab5", 526: "Cab6", 527: "Cab7", 528: "Cab8"}
OLD = "2026-10-19 photos show 3 shelves + floor -- confirm against the prints before building"
NEW = ("4 adjustable/removable shelves + the cabinet floor = 5 levels (Scott, 2026-10-19: "
       "16 shelves across the four uppers, as ordered on GC-8103); each shelf 14 in deep x "
       "26.5 in wide, Scott measured. Levels will be")

plans = []
for pk, name in UPPERS.items():
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
