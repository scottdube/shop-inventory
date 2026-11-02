"""Enter the NooElec NESDR Mini (part 261) found at LRD, 2026-11-02.

Identified from the case: "NooElec R820T SDR & DVB-T NESDR Mini", MCX input
with an MCX-to-SMA adapter fitted. Part 261 existed with no stock row anywhere.
Its purchase note shows 1 unit lifetime (Amazon, $21.95), so this is probably
that unit; not established, so no price is set. Scott: going into the Raspberry
Pi / SBC tub, which is not loaded yet, so it is recorded in LRD/Receiving beside
the Pis (840, 841) and the microSD (1229) and moves with them. Count 1 (one
dongle in the photo, "also going into the pie tub"). Part default (bare SLN
root) is left alone until the tub has a location.

    itq run scripts/nesdr_mini_lrd_1102.py [--commit]
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

p = Part.objects.get(pk=261)
assert p.name.startswith("NooElec NESDR Mini"), p.name
assert not StockItem.objects.filter(part=p).exists(), "261 has stock now - merge, don't add"
rcv = StockLocation.objects.get(pathstring="LRD/Receiving")
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
print(f"part 261 x1 -> {rcv.pathstring}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

s = StockItem(part=p, location=rcv, quantity=1)
s.save()
Note.objects.create(content_object=s, title="Source", primary=True,
                    content="Found at LRD 2026-11-02, MCX-to-SMA adapter fitted. Going into the Raspberry Pi / SBC "
                            "tub with the Pis (840, 841) and microSD (1229); recorded in Receiving until that tub "
                            "is loaded. Probably the part's only purchase (Amazon, 1 unit lifetime, $21.95); not "
                            "established, so no price is set.")
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 1.0},
                     notes="With the Raspberry Pis, pending the Pi / SBC tub.")

# Verify by re-read: .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=s.pk)
print(f"stock {s.pk}: part {s.part_id} {s.part.name[:60]} x{s.quantity:g} @ {s.location.pathstring}")
print("ALL VERIFIED" if s.quantity == 1 and s.location_id == rcv.pk and s.notes.exists() else "NOT VERIFIED")
