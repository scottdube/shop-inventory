"""Enter C&K 8121 pushbuttons x12 at LRD, F1-R4C3, 2026-11-02.

Identified from the marks on the bushing plate: 8121, C&K, U.S.A. That is C&K's
8100-series SPDT momentary pushbutton with PC pins. No part existed. The
nearest is part 754, the C&K 8168 with panel bezel, a different switch, so a
new part goes in 754's category. Count 12 from Scott. No source was given, so
the price is left unset.

    itq run scripts/ck8121_lrd_1102.py [--commit]
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

NAME = "C&K 8121 Push Button SPDT Momentary, PC pins"
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R4C3")
sib = Part.objects.get(pk=754)
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
held = StockItem.objects.filter(location=loc)
assert not held.exists(), f"F1-R4C3 already holds {list(held.values_list('pk', 'part__name'))}"
dup = list(Part.objects.filter(name__icontains="8121"))
assert len(dup) <= 1, dup
print(f"{NAME} x12 -> {loc.pathstring} in {sib.category.pathstring}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

p = dup[0] if dup else Part.objects.create(
    name=NAME, category=sib.category, component=True, purchaseable=True, default_location=loc,
    description="C&K 8100-series pushbutton, SPDT momentary, threaded bushing, white plunger, "
                "red body, 3 PC pins. Marked 8121 C&K U.S.A.")
s = StockItem(part=p, location=loc, quantity=12)
s.save()
Note.objects.create(content_object=s, title="Source", primary=True,
                    content="Counted by Scott at put-away, 2026-11-02. Source not stated.")
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 12.0}, notes="Into F1-R4C3.")

# Verify by re-read: .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=s.pk)
p = Part.objects.get(pk=p.pk)
print(f"stock {s.pk}: part {p.pk} {p.name} x{s.quantity:g} @ {s.location.pathstring}")
ok = s.quantity == 12 and s.location_id == loc.pk and s.notes.exists() and p.default_location_id == loc.pk
print("ALL VERIFIED" if ok else "NOT VERIFIED")
