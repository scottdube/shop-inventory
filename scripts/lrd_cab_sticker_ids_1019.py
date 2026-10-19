"""Note each LRD cabinet's part-label product ID in its description.

Scott, 2026-10-19: keep Cab1..Cab8 (the 2026 design render's numbers) and record
the 2025 product IDs printed on the cabinets' part labels alongside. The labels
are what you read at the cabinet; the blueprints use them too.

Dry run by default; --commit writes and re-reads.
"""
import os, sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
# pk -> (expected name, part-label product ID)
IDS = {529: ("Cab1", 3), 530: ("Cab2", 5), 531: ("Cab3", 7), 532: ("Cab4", 9),
       525: ("Cab5", 2), 526: ("Cab6", 4), 527: ("Cab7", 6), 528: ("Cab8", 8)}
WALL_PK = 524


def new_desc(d, n, pid):
    prefix = f"Installer #{n}. "
    assert d.startswith(prefix), d[:40]
    return (f"Design-render #{n}; part-label product ID {pid} (blueprints use the label ID). "
            + d[len(prefix):])


plans = []
for pk, (name, pid) in IDS.items():
    loc = StockLocation.objects.get(pk=pk)
    assert loc.name == name, (pk, loc.name)
    plans.append((loc, new_desc(loc.description, name[3:], pid)))
    print(f"{'WRITE' if COMMIT else 'would'} {name}: label ID {pid}")

wall = StockLocation.objects.get(pk=WALL_PK)
old_wall = ("Cabinets carry the installer's numbers Cab1-Cab8 (2026-10-19); 9 is the "
            "worktop and is not a location.")
new_wall = ("Cabinets are named Cab1-Cab8 after the 2026 design render (9 = worktop, not a "
            "location). The part labels on the cabinets carry the 2025 product IDs instead: "
            "uppers 2/4/6/8, door base 3, drawer banks 5/7/9, countertop 1 -- each cabinet's "
            "description gives its label ID.")
assert old_wall in wall.description
print(f"{'WRITE' if COMMIT else 'would'} wall description")

if COMMIT:
    for loc, d in plans:
        loc.description = d
        loc.save()
    wall.description = wall.description.replace(old_wall, new_wall)
    wall.save()
    bad = 0
    for loc, d in plans:
        ok = StockLocation.objects.get(pk=loc.pk).description == d
        bad += not ok
        print(f"  {'OK ' if ok else 'BAD'} {loc.name}")
    ok = new_wall in StockLocation.objects.get(pk=WALL_PK).description
    bad += not ok
    print(f"  {'OK ' if ok else 'BAD'} wall")
    print("ALL VERIFIED" if not bad else f"{bad} NOT WRITTEN")
