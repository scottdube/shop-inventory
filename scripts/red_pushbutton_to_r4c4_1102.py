"""Move the red-cap push buttons (stock 1219, part 1483) from F1-R4C5 to F1-R4C4, 2026-11-02.

Scott put them in R4C4 with the ITT hex switches, not the proposed R4C5; his
answer arrived after red_pushbutton_lrd_1102.py had run. The part's
default_location follows, since R4C4 is the only place they live.

    itq run scripts/red_pushbutton_to_r4c4_1102.py [--commit]
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

dst = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R4C4")
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
s = StockItem.objects.get(pk=1219)
p = s.part
assert p.pk == 1483 and s.location.name == "F1-R4C5", (p.pk, s.location)
print(f"stock 1219 x{s.quantity:g}: {s.location.pathstring} -> {dst.pathstring}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

s.move(dst, "Scott stowed these in F1-R4C4, not R4C5.", u)
p.default_location = dst
p.save()

# Verify by re-read: .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=1219)
p.refresh_from_db()
print(f"stock 1219 @ {s.location.pathstring} x{s.quantity:g}; part default {p.default_location.pathstring}")
print("ALL VERIFIED" if s.location_id == dst.pk and p.default_location_id == dst.pk and s.quantity == 3 else "NOT VERIFIED")
