"""Enter ITT 16-position hex rotary DIP switches x4 at LRD, F1-R4C4, 2026-11-02.

Identified from the part: ITT logo on the base, positions 0-9 A-F around a
screwdriver-slot rotor, PC pins. ITT owned C&K in that era. The code type
(real/complement) and pinout are not marked on the visible faces, so they're not
recorded. No part existed (searched hex / BCD / coded / rotary / ITT). A new part
goes in 744's category (Switches). R4C4, not R4C3 with the C&K toggles: C3
already holds four kinds. Count 4 from Scott; R4C4 on his yes. Source not
stated, so the price is left unset.

    itq run scripts/itt_hex_switch_lrd_1102.py [--commit]
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

NAME = "ITT Rotary DIP Switch, 16-position hex (0-F), screwdriver adjust, PC pins"
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R4C4")
sib = Part.objects.get(pk=744)
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
held = StockItem.objects.filter(location=loc)
assert not held.exists(), f"F1-R4C4 already holds {list(held.values_list('pk', 'part__name'))}"
dup = list(Part.objects.filter(name=NAME))
assert len(dup) <= 1, dup
print(f"{NAME} x4 -> {loc.pathstring} in {sib.category.pathstring}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

p = dup[0] if dup else Part.objects.create(
    name=NAME, category=sib.category, component=True, purchaseable=True, default_location=loc,
    description="ITT (C&K) 16-position hexadecimal rotary DIP switch, 0-9 A-F, slotted rotor, "
                "through-hole. Code type and pinout not marked: check before designing in.")
s = StockItem(part=p, location=loc, quantity=4)
s.save()
Note.objects.create(content_object=s, title="Source", primary=True,
                    content="Found at LRD; counted by Scott at put-away, 2026-11-02. Source not stated.")
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 4.0}, notes="Into F1-R4C4.")

# Verify by re-read: .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=s.pk)
p = Part.objects.get(pk=p.pk)
print(f"stock {s.pk}: part {p.pk} {p.name} x{s.quantity:g} @ {s.location.pathstring}")
ok = s.quantity == 4 and s.location_id == loc.pk and s.notes.exists() and p.default_location_id == loc.pk
print("ALL VERIFIED" if ok else "NOT VERIFIED")
