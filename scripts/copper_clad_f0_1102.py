"""Move the copper clad blanks (stock 285) from the bare LRD root to F0-R1C1, 2026-11-02.

LRD stock since 2026-08-19, not part of the carry. Not found during the F1 fill;
Scott found it later and stowed it in F0-R1C1. It goes in F0 because the 7x10 cm
boards don't lie flat in an F1 bin. Part 789's default_location becomes this cell
only if it is blank or the bare LRD root; an SLN home is left alone.

    itq run scripts/copper_clad_f0_1102.py [--commit]
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

loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F0/F0-R1C1")
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
s = StockItem.objects.get(pk=285)
p = s.part
assert p.pk == 789 and s.location.pathstring == "LRD", (p.pk, s.location.pathstring)
held = StockItem.objects.filter(location=loc)
assert not held.exists(), f"F0-R1C1 already holds {list(held.values_list('pk', 'part__name'))}"
set_default = p.default_location is None or p.default_location.pathstring == "LRD"
print(f"stock 285 {p.name} x{s.quantity:g}: {s.location.pathstring} -> {loc.pathstring}; "
      f"part default {p.default_location} -> {'F0-R1C1' if set_default else 'unchanged'}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

s.move(loc, "Stowed by Scott in F0-R1C1, 2026-11-02 (was on the bare LRD root).", u)
if set_default:
    p.default_location = loc
    p.save()

# Verify by re-read: .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=285)
p.refresh_from_db()
print(f"stock 285 @ {s.location.pathstring} x{s.quantity:g}; part default {p.default_location}")
ok = s.location_id == loc.pk and s.quantity == 10 and (not set_default or p.default_location_id == loc.pk)
print("ALL VERIFIED" if ok else "NOT VERIFIED")
