"""Mark LRD RB-15 as the Condensate Doser kit, and enter an Amazon Basics 128 GB microSD card, 2026-11-02.

- RB-15: Scott put the Kamoer NKP pump (PO-0275, received to RB-15 by
  receive_po.py as stock 1228) there, so the bin becomes the doser's kit bin.
  RB-15 is VERIFIED EMPTY at SLN, so the number names no kit up north. Part
  1459's default_location is left blank: a project bin is never a spare's home.
- microSD: Amazon Basics microSDXC 128 GB, UHS-I U3 V30 A2, with SD adapter, in
  its clear case. No part existed (searched micro SD, microSD, SDXC, memory card,
  SD card, 128GB, Amazon Basics). Scott: "I've put the micro SD card with the
  pies" - the Pis (840, 841) are still recorded in LRD/Receiving because the
  Raspberry Pi / SBC tub is not loaded yet, so the card is recorded there too
  and moves with them. Count 1 ("the micro SD card"). Source not stated, no price.

    itq run scripts/doser_bin_microsd_1102.py [--commit]
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.db.models import Q  # noqa: E402
from InvenTree.status_codes import StockHistoryCode  # noqa: E402
from common.models import Note  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

RB15_DESC = ("CONDENSATE DOSER project kit (part 1460) - Kamoer NKP 12 V peristaltic pump (stock 1228, "
             "PO-0275). Loaded by Scott 2026-11-02. LRD only; SLN RB-15 is empty.")
rb15 = StockLocation.objects.get(pathstring="LRD/Electronics Bench/Red Bins/RB-15")
rcv = StockLocation.objects.get(pathstring="LRD/Receiving")
cat = PartCategory.objects.get(pathstring="Modules")
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
held = list(StockItem.objects.filter(location=rb15).values_list("pk", flat=True))
assert held == [1228], held
assert rb15.description.startswith("Red bin. Holds ONE"), rb15.description
dup = list(Part.objects.filter(Q(name__icontains="microSD") | Q(name__icontains="micro SD")
                               | Q(name__icontains="SDXC")).values_list("pk", "name"))
assert not dup, dup
NAME = "Amazon Basics microSDXC 128GB A2 U3 V30 with SD Adapter"
print(f"RB-15 description -> {RB15_DESC}")
print(f"new part in {cat.pathstring}: {NAME}; x1 -> {rcv.pathstring}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

StockLocation.objects.filter(pk=rb15.pk).update(description=RB15_DESC)
p = Part.objects.create(
    name=NAME, category=cat, component=True, purchaseable=True,
    description="Amazon Basics microSDXC memory card, 128 GB, UHS-I, U3, V30, A2, Class 10, "
                "with full-size SD adapter, in a clear case. Identified from the card.")
s = StockItem(part=p, location=rcv, quantity=1)
s.save()
Note.objects.create(content_object=s, title="Source", primary=True,
                    content="Found at LRD 2026-11-02; Scott put it with the Raspberry Pis (840, 841), which "
                            "are recorded in Receiving until the Raspberry Pi / SBC tub is loaded. Moves with "
                            "them. Count 1 (Scott). Source not stated.")
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 1.0},
                     notes="With the Raspberry Pis, pending the Pi / SBC tub.")

# Verify by re-read: .save() on this install has reported success and written nothing.
rb15 = StockLocation.objects.get(pk=rb15.pk)
s = StockItem.objects.get(pk=s.pk)
print(f"RB-15: {rb15.description}")
print(f"stock {s.pk}: part {s.part_id} {s.part.name} x{s.quantity:g} @ {s.location.pathstring}")
ok = rb15.description == RB15_DESC and s.quantity == 1 and s.location_id == rcv.pk and s.notes.exists()
print("ALL VERIFIED" if ok else "NOT VERIFIED")
