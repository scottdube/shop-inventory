"""Enter 1 INMP441 I2S MEMS microphone (part 55) found at LRD, into F1-R2C6, 2026-11-02.

Identified from the silkscreen (round board, SCK/WS/L-R/SD/VDD/GND, mic logo).
Part 55 already existed with no stock anywhere and is on no BOM. Its only
purchase record is Amazon 2026-04-06 (Teyleten 5-pack); this one is probably
from that order, but that isn't established, so no price is set.

Part 55's default_location was the bare SLN root, which is no home. All of its
stock is now this row, so R2C6 becomes the default.

    itq run scripts/inmp441_lrd_1102.py [--commit]
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from InvenTree.status_codes import StockHistoryCode  # noqa: E402
from common.models import Note  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

p = Part.objects.get(pk=55)
assert p.name.startswith("INMP441"), p.name
assert not StockItem.objects.filter(part=p).exists(), "55 has stock now - merge, don't add"
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R2C6")
held = StockItem.objects.filter(location=loc)
assert not held.exists(), f"F1-R2C6 already holds {list(held.values_list('pk', 'part__name'))}"
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
print(f"part 55 x1 -> {loc.pathstring}; default {p.default_location} -> F1-R2C6")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

s = StockItem(part=p, location=loc, quantity=1)
s.save()
Note.objects.create(content_object=s, title="Source", primary=True, content=(
    "Found at LRD; counted by Scott at put-away, 2026-11-02. Probably from Amazon 2026-04-06 "
    "(Teyleten 5-pack), the part's only purchase record; not established, so no price is set."))
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 1.0}, notes="Into F1-R2C6.")
p.default_location = loc
p.save()

# Verify by re-read: .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=s.pk)
p.refresh_from_db()
print(f"stock {s.pk}: {p.name} x{s.quantity:g} @ {s.location.pathstring}; part default {p.default_location.pathstring}")
ok = s.quantity == 1 and s.location_id == loc.pk and s.notes.exists() and p.default_location_id == loc.pk
print("ALL VERIFIED" if ok else "NOT VERIFIED")
