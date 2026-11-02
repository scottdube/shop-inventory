"""Enter C&K 7101 toggles x7 at LRD, F1-R4C3, with the other C&K switches (2026-11-02).

Marked 7101 C&K U.S.A.: SPDT ON-ON, 3 pins. Part 744 already covers it; its
note lists 7101 among the markings in the SLN lot. So this is a new LRD row of
744, not a new part. 744's default_location stays at its SLN home: a part has
one default, and the SLN drawer is where its main stock lives (same as the
1N4001 row in R3C2). Count 7 from Scott. No source was given, so the price is
left unset.

    itq run scripts/ck7101_lrd_1102.py [--commit]
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

loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R4C3")
p = Part.objects.get(pk=744)
assert p.name == "C&K Miniature Toggle Switch SPDT ON-ON", p.name
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
here = StockItem.objects.filter(part=p, location=loc)
assert not here.exists(), f"744 already has a row in R4C3: {list(here.values_list('pk', 'quantity'))} - merge"
print(f"744 rows now: {[(s.pk, s.quantity, s.location.pathstring) for s in StockItem.objects.filter(part=p)]}; "
      f"default {p.default_location}")
print(f"would add x7 at {loc.pathstring}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

s = StockItem(part=p, location=loc, quantity=7)
s.save()
Note.objects.create(content_object=s, title="Source", primary=True,
                    content="Counted by Scott at put-away, 2026-11-02. Marked 7101 C&K U.S.A. Source not stated.")
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 7.0}, notes="Into F1-R4C3.")

# Verify by re-read: .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=s.pk)
print(f"stock {s.pk}: part {s.part_id} {s.part.name} x{s.quantity:g} @ {s.location.pathstring}")
ok = s.part_id == 744 and s.quantity == 7 and s.location_id == loc.pk and s.notes.exists()
print("ALL VERIFIED" if ok else "NOT VERIFIED")
