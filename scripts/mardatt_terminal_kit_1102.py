"""Enter the Mardatt 5.08 mm pluggable terminal block kit into LRD Cab2-D3, 2026-11-02.

Identified from the lid card: "Mardatt, 32Pcs 5.08mm Pitch 2P-10P Pluggable
Teminal Blocks Connector Socket", male + female pairs. No part existed (searched
Mardatt, pluggable, 5.08 terminal, terminal kits/sets), so one is created in
Electronics/Connectors/Terminals. An assortment is ONE kit unit, not 32 pieces.

Count from Scott: all as sold except 4P, which has 4 of 5, so 31 of 32.
It doesn't fit an F0 cell; Scott put it in Cab2-D3 with other kits, which he
calls temporary ("will eventually get moved probably"), so default_location is
left blank rather than pointing a spare's home at a staging drawer.
Source not stated, so no price.

    itq run scripts/mardatt_terminal_kit_1102.py [--commit]
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

NAME = "Mardatt Pluggable Terminal Block Kit 5.08mm, 2P-10P, 32 pcs"
CONTENTS = ("As sold: male & female pairs, 5.08 mm pitch - 2P x6, 3P x6, 4P x5, 5P x5, 6P x2, 7P x2, "
            "8P x2, 9P x2, 10P x2 = 32.")
d3 = StockLocation.objects.get(pathstring="LRD/Countertop Wall/Cab2/Cab2-D3")
cat = PartCategory.objects.get(pathstring="Electronics/Connectors/Terminals")
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
dup = list(Part.objects.filter(Q(name__icontains="mardatt") | Q(name__icontains="pluggable"))
           .values_list("pk", "name"))
assert not dup, dup
print(f"new part in {cat.pathstring}: {NAME}; x1 kit -> {d3.pathstring}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

p = Part.objects.create(name=NAME, category=cat, component=True, purchaseable=True,
                        description="Mardatt pluggable (2-piece) PCB terminal block assortment, 5.08 mm pitch, "
                                    "green, 2 to 10 positions, male header + female screw plug. " + CONTENTS)
s = StockItem(part=p, location=d3, quantity=1)
s.save()
Note.objects.create(content_object=s, title="Source", primary=True,
                    content=f"Found at LRD; counted by Scott 2026-11-02. {CONTENTS} On hand 31 of 32: all as sold "
                            "except 4P, 4 of 5. In Cab2-D3 TEMPORARILY with other kits (won't fit an F0 cell); "
                            "Scott expects to move it. Source not stated.")
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 1.0},
                     notes="Into Cab2-D3 (temporary).")

# Verify by re-read: .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=s.pk)
print(f"stock {s.pk}: part {s.part_id} {s.part.name} x{s.quantity:g} @ {s.location.pathstring}")
print("ALL VERIFIED" if s.quantity == 1 and s.location_id == d3.pk and s.notes.exists() else "NOT VERIFIED")
