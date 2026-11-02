"""Move the Athom ESPHome plugs (stock 1096) from LRD/Receiving to the Smart Switches & Plugs Tub, 2026-11-02.

Scott: "Yes in tub". The tub's own place is still temporary (Scott), so the
location stays under LRD/Countertop Wall until it gets a shelf. Part default
becomes the tub only if it is blank or a staging area.

    itq run scripts/athom_plugs_to_tub_1102.py [--commit]
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

tub = StockLocation.objects.get(pathstring="LRD/Countertop Wall/Smart Switches & Plugs Tub")
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
s = StockItem.objects.get(pk=1096)
p = s.part
assert p.name.startswith("Athom US V2 Smart Plug") and s.location.pathstring == "LRD/Receiving", (p.name, s.location)
qty = s.quantity
set_default = p.default_location is None or p.default_location.pathstring in ("LRD", "LRD/Receiving")
print(f"stock 1096 {p.name} x{qty:g}: {s.location.pathstring} -> {tub.pathstring}; "
      f"part default {p.default_location} -> {'tub' if set_default else 'unchanged'}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

s.move(tub, "Put in the Smart Switches & Plugs tub by Scott, 2026-11-02.", u)
if set_default:
    p.default_location = tub
    p.save()

# Verify by re-read: .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=1096)
p.refresh_from_db()
print(f"stock 1096 @ {s.location.pathstring} x{s.quantity:g}; part default {p.default_location}")
ok = s.location_id == tub.pk and s.quantity == qty and (not set_default or p.default_location_id == tub.pk)
print("ALL VERIFIED" if ok else "NOT VERIFIED")
