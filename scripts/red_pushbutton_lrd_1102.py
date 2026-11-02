"""Enter miniature red-cap momentary push buttons x3 at LRD, F1-R4C5, 2026-11-02.

Black body, threaded nickel bushing, red cap, 2 solder lugs, no markings: the
PBS-110 style of part 749 (black cap, SLN), but a different cap color, so a new
part rather than a row of 749. Not part 750 either: that is the vintage
phenolic assortment with unsorted action; these are 3 identical, and Scott says
momentary. Count 3 and action from Scott; R4C5 as proposed. Source not stated,
so the price is left unset.

    itq run scripts/red_pushbutton_lrd_1102.py [--commit]
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

NAME = "Push Button, miniature panel mount, momentary, black body, red cap (PBS-110 style)"
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R4C5")
sib = Part.objects.get(pk=749)
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
held = StockItem.objects.filter(location=loc)
assert not held.exists(), f"F1-R4C5 already holds {list(held.values_list('pk', 'part__name'))}"
dup = list(Part.objects.filter(name=NAME))
assert len(dup) <= 1, dup
print(f"{NAME} x3 -> {loc.pathstring} in {sib.category.pathstring}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

p = dup[0] if dup else Part.objects.create(
    name=NAME, category=sib.category, component=True, purchaseable=True, default_location=loc,
    description="Miniature panel-mount momentary push button, black body, red cap, threaded nickel "
                "bushing, 2 solder lugs. Unmarked. Same style as PBS-110 (part 749, black cap).")
s = StockItem(part=p, location=loc, quantity=3)
s.save()
Note.objects.create(content_object=s, title="Source", primary=True,
                    content="Found at LRD; counted by Scott at put-away, 2026-11-02. Momentary per Scott. "
                            "Source not stated.")
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 3.0}, notes="Into F1-R4C5.")

# Verify by re-read: .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=s.pk)
p = Part.objects.get(pk=p.pk)
print(f"stock {s.pk}: part {p.pk} {p.name} x{s.quantity:g} @ {s.location.pathstring}")
ok = s.quantity == 3 and s.location_id == loc.pk and s.notes.exists() and p.default_location_id == loc.pk
print("ALL VERIFIED" if ok else "NOT VERIFIED")
