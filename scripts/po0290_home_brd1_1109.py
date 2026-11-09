"""PO-0290 Xiaomi precision screwdriver: received to LRD/Countertop Wall (where it is),
home = LRD/Electronics Bench/BR/BR-D1 (where Scott says it will end up once the right
pedestal is assembled). Scott 2026-11-09: "that's going to live on the work surface or
the countertop, but it will end up in BRD1." default_location is the spare's home, never
a staging spot, so the countertop is the row's location and BR-D1 is the part's default.
Dry run by default; --commit writes. Re-reads every write."""
import os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db import transaction
from part.models import Part
from stock.models import StockItem, StockLocation
from plugins.notes_compat import note_text, note_append

COMMIT = "--commit" in sys.argv
PART, COUNTERTOP, BRD1 = 1515, 524, 856
part = Part.objects.get(pk=PART); home = StockLocation.objects.get(pk=BRD1)
assert home.pathstring == "LRD/Electronics Bench/BR/BR-D1", home.pathstring
row = StockItem.objects.get(part=part, location_id=COUNTERTOP)

class DryRun(Exception):
    pass

try:
    with transaction.atomic():
        Part.objects.filter(pk=part.pk).update(default_location=home)
        part.refresh_from_db(); assert part.default_location_id == BRD1
        note_append(row, "Scott 2026-11-09: on the countertop / work surface for now; goes to BR-D1 "
                         "(right pedestal drawer 1) once the LRD bench pedestal is assembled. "
                         "default_location set to BR-D1 the same day.")
        assert "goes to BR-D1" in note_text(row)
        print(f"stock {row.pk} {part.full_name} at {row.location.pathstring}; part default_location -> {part.default_location.pathstring}")
        if not COMMIT:
            raise DryRun()
except DryRun:
    print("DRY RUN - rolled back. Re-run with --commit.")
else:
    print(f"COMMITTED  http://192.168.50.10:8001/web/stock/item/{row.pk}")
