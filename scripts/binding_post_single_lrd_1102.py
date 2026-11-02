"""Enter single panel-mount binding posts at LRD, F1-R5C8, 2026-11-02: red x5, black x3.

No single-post part existed. The only binding-post part is 733, a red + black
PAIR on a shared base, which is a different item. The new part goes in the same
category as 733 and the same drawer: binding posts are one kind, so both share
R5C8, as the diodes share R3C2. One part per colour: a red and a black post
are not interchangeable on a panel. Counts from Scott. No source was given, so the
price is left unset.

    itq run scripts/binding_post_single_lrd_1102.py --color red --qty 5 [--commit]
    itq run scripts/binding_post_single_lrd_1102.py --color black --qty 3 [--commit]
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
ap.add_argument("--color", choices=["red", "black"], required=True)
ap.add_argument("--qty", type=int, required=True)
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

NAME = f"Binding Post, single, {a.color}, panel mount"
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R5C8")
pair = Part.objects.get(pk=733)
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
dup = list(Part.objects.filter(name=NAME))
assert len(dup) <= 1, dup
print(f"{NAME} x{a.qty} -> {loc.pathstring} in {pair.category.pathstring}; drawer holds "
      f"{list(StockItem.objects.filter(location=loc).values_list('pk', 'part__name'))}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

p = dup[0] if dup else Part.objects.create(
    name=NAME, category=pair.category, component=True, purchaseable=True, default_location=loc,
    description=f"Single binding post, {a.color} ribbed plastic cap, threaded panel-mount body with "
                "nickel hex nut, solder/wire stud. Not the red+black pair on a base (part 733).")
s = StockItem(part=p, location=loc, quantity=a.qty)
s.save()
Note.objects.create(content_object=s, title="Source", primary=True,
                    content="Counted by Scott at put-away, 2026-11-02. Source not stated.")
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": float(a.qty)}, notes="Into F1-R5C8.")

# Verify by re-read: .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=s.pk)
p = Part.objects.get(pk=p.pk)
print(f"stock {s.pk}: part {p.pk} {p.name} x{s.quantity:g} @ {s.location.pathstring}")
ok = s.quantity == a.qty and s.location_id == loc.pk and s.notes.exists() and p.default_location_id == loc.pk
print("ALL VERIFIED" if ok else "NOT VERIFIED")
