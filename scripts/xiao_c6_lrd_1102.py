"""Enter 3 XIAO ESP32-C6 boards (part 105) found at LRD, F1-R1C4, 2026-11-02.

Identified from the shield can: Seeed Studio, Model XIAO-ESP32-C6. Part 105 is the
board; 64 and 232 are vendor "pack" listings with no stock, so they are not used.
F1-R1C4 is the dev-board cell next to the XIAO S3 spares (R1C3), on Scott's yes.
Count 3 from Scott. Source not stated, so the price is left unset. Part 105's
default_location stays at SLN B3-R6C3, where the main stock (8) lives.

    itq run scripts/xiao_c6_lrd_1102.py [--commit]
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

p = Part.objects.get(pk=105)
assert p.name == "Seeed Studio XIAO ESP32-C6", p.name
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R1C4")
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
held = StockItem.objects.filter(location=loc)
assert not held.exists(), f"F1-R1C4 already holds {list(held.values_list('pk', 'part__name'))}"
print(f"part 105 {p.name} x3 -> {loc.pathstring}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

s = StockItem(part=p, location=loc, quantity=3)
s.save()
Note.objects.create(content_object=s, title="Source", primary=True,
                    content="Found at LRD; counted by Scott at put-away, 2026-11-02. Source not stated.")
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 3.0}, notes="Into F1-R1C4.")

# Verify by re-read: .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=s.pk)
print(f"stock {s.pk}: {s.part.name} x{s.quantity:g} @ {s.location.pathstring}")
ok = s.part_id == 105 and s.quantity == 3 and s.location_id == loc.pk and s.notes.exists()
print("ALL VERIFIED" if ok else "NOT VERIFIED")
