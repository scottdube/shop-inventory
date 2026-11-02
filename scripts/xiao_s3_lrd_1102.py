"""Enter 2 XIAO ESP32-S3 boards (part 101) found at LRD, 2026-11-02.

Identified from the shield can: Seeed Studio, Model XIAO-ESP32-S3, in Seeed's
round puck case. Scott: qty 2, one going to the Info Orb v2 board. They are NOT
stock 1, the voice-assistant XIAO in Receiving: Scott says that board is a
different form factor (so stock 1 is likely mis-recorded as part 101; noted in
the fill plan, not fixed here).

- Spare x1 -> F1-R1C3, the dev-board cell held for the Supermini S3 (stock 78,
  still not found).
- Orb x1 -> LRD/Receiving, beside the Info Orbs PCBs (796): the LRD red bins
  don't exist in InvenTree yet, so the kit is still recorded there. It moves
  with 796 when the Info Orbs RB is made. Kept as its own row because it is
  earmarked, not interchangeable spare stock.

Source not stated, so the price is left unset. Part 101's default_location stays
at SLN B3-R3C4, where the main stock lives.

    itq run scripts/xiao_s3_lrd_1102.py [--commit]
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

p = Part.objects.get(pk=101)
assert p.name == "Seeed Studio XIAO ESP32-S3", p.name
c3 = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R1C3")
rcv = StockLocation.objects.get(pathstring="LRD/Receiving")
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
held = StockItem.objects.filter(location=c3)
assert not held.exists(), f"F1-R1C3 already holds {list(held.values_list('pk', 'part__name'))}"
ROWS = [
    (c3, "Into F1-R1C3 (spare).",
     "Found at LRD; counted by Scott 2026-11-02 (2 boards, this is the spare). Source not stated."),
    (rcv, "Earmarked for the Info Orb v2 board; with the Info Orbs PCBs (796) until the LRD red bins exist.",
     "Found at LRD; counted by Scott 2026-11-02 (2 boards). EARMARKED: Info Orb v2 board (Scott). "
     "Recorded in Receiving with the Info Orbs PCBs (796); moves with them to the Info Orbs red bin. "
     "Source not stated."),
]
for loc, why, _ in ROWS:
    print(f"part 101 x1 -> {loc.pathstring}: {why}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

made = []
for loc, why, note in ROWS:
    s = StockItem(part=p, location=loc, quantity=1)
    s.save()
    Note.objects.create(content_object=s, title="Source", content=note, primary=True)
    s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 1.0}, notes=why)
    made.append((s.pk, loc.pk))

# Verify by re-read: .save() on this install has reported success and written nothing.
bad = []
for pk, loc_pk in made:
    s = StockItem.objects.get(pk=pk)
    print(f"stock {s.pk}: {s.part.name} x{s.quantity:g} @ {s.location.pathstring}")
    if s.part_id != 101 or s.quantity != 1 or s.location_id != loc_pk or not s.notes.exists():
        bad.append(pk)
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
