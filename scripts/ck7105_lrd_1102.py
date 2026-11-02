"""Enter C&K 7105 toggles x4 at LRD, F1-R4C3, with the other C&K switches (2026-11-02).

Identified from the marks on the body: 7105, C&K, U.S.A. That is C&K's 7000-series
miniature toggle, SPDT ON-OFF-ON (center off), 3 PC pins, long bare aluminum bat
with no cap, keyway in the bushing. No part existed: 744 is SPDT ON-ON and 745 is
SPDT momentary, so neither covers a center-off switch. A new part goes in 744's
category. Count 4 from Scott; F1-R4C3 on his yes. No source was given, so the
price is left unset.

    itq run scripts/ck7105_lrd_1102.py [--commit]
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

NAME = "C&K 7105 Miniature Toggle Switch SPDT ON-OFF-ON, PC pins"
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R4C3")
sib = Part.objects.get(pk=744)
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
dup = list(Part.objects.filter(name__icontains="7105"))
assert len(dup) <= 1, dup
print(f"{NAME} x4 -> {loc.pathstring} in {sib.category.pathstring}; drawer holds "
      f"{list(StockItem.objects.filter(location=loc).values_list('pk', 'part__name'))}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

p = dup[0] if dup else Part.objects.create(
    name=NAME, category=sib.category, component=True, purchaseable=True, default_location=loc,
    description="C&K 7000-series miniature toggle, SPDT ON-OFF-ON (center off, maintained), threaded "
                "bushing with keyway, long bare aluminum bat, 3 PC pins. Marked 7105 C&K U.S.A.")
s = StockItem(part=p, location=loc, quantity=4)
s.save()
Note.objects.create(content_object=s, title="Source", primary=True,
                    content="Counted by Scott at put-away, 2026-11-02. Source not stated.")
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 4.0}, notes="Into F1-R4C3.")

# Verify by re-read: .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=s.pk)
p = Part.objects.get(pk=p.pk)
print(f"stock {s.pk}: part {p.pk} {p.name} x{s.quantity:g} @ {s.location.pathstring}")
ok = s.quantity == 4 and s.location_id == loc.pk and s.notes.exists() and p.default_location_id == loc.pk
print("ALL VERIFIED" if ok else "NOT VERIFIED")
