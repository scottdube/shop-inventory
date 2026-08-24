"""Move the Z-axis way cover from Receiving to the machine it is waiting on.

Scott, 2026-08-24: *"It's just the z axis cover. Nothing else. And it's sitting
at the eleven hundred MX waiting to be installed."*

Two observations in that sentence, and they are exactly the two a receipt cannot
make: WHAT (one cover, nothing else in the box) and WHERE (at the mill). A
person held it and looked. Per docs/TRAPS.md that is a put-away, so this stamps
a stocktake_date - the receipt on its own correctly did not.

NOT set: default_location. SLN/Machine Shop is where this cover is STAGED, not
where a spare of it goes home, and the location policy is explicit that a
staging area must never become a default_location. There is also no spare to
send home: this one is about to be fitted.

NOT done: into_service. The cover is beside the mill, not on it. `belongs_to`
means FITTED, and claiming it now would be the same class of error as a receipt
claiming a drawer. When it is actually bolted on:

    itq run scripts/into_service.py --part 1085 --tool 546
    itq run scripts/into_service.py --part 1085 --tool 546 --commit

Part #546 (Tormach 1100MX Mill) already has exactly one stock row, so that call
will not hit the must-be-stocked-first guard.
"""
import argparse
import datetime
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth import get_user_model      # noqa: E402
from stock.models import StockItem, StockLocation   # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()
DRY = not a.commit

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
si = StockItem.objects.get(pk=665)
dest = StockLocation.objects.get(pk=420)
assert dest.pathstring == "SLN/Machine Shop", dest.pathstring
assert si.part.pk == 1085, f"stock #665 is part #{si.part.pk}, expected 1085"

print(f"stock #{si.pk} {si.part.name[:50]}")
print(f"  from {si.location.pathstring if si.location else '-'} -> {dest.pathstring}")
print(f"  stocktake {si.stocktake_date} -> {datetime.date(2026, 8, 24)}")
print(f"  belongs_to stays {si.belongs_to} (NOT fitted yet)")

if DRY:
    print("\nDRY RUN - nothing written")
    sys.exit(0)

si.move(dest, "Staged at the 1100MX awaiting installation, 2026-08-24.", user)

NOTE = ("At the Tormach 1100MX, staged for installation. Scott confirmed 2026-08-24 that "
        "the box held the Z-axis cover and nothing else, and that it is sitting at the "
        "machine - so quantity and location are both observed by a person, which is why "
        "this row carries a stocktake_date and the receipt into Receiving did not. "
        "NOT yet fitted: belongs_to is still null on purpose. When it is bolted on, use "
        "scripts/into_service.py --part 1085 --tool 546, because stock means spares and a "
        "fitted cover is not one. default_location deliberately left unset - Machine Shop "
        "is staging, not a home for a spare.")
StockItem.objects.filter(pk=665).update(
    stocktake_date=datetime.date(2026, 8, 24), notes=NOTE)

f = StockItem.objects.get(pk=665)
assert f.location and f.location.pk == 420, "move did not stick"
assert f.stocktake_date == datetime.date(2026, 8, 24), "stocktake did not stick"
assert f.belongs_to is None, "belongs_to should still be null"
print(f"+ stock #{f.pk} qty={float(f.quantity):g} @ {f.location.pathstring} "
      f"stocktake={f.stocktake_date} belongs_to={f.belongs_to}")
print(f"  part #1085 default_location={StockItem.objects.get(pk=665).part.default_location} (left unset)")
