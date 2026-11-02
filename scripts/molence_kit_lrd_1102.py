"""Enter 1 unopened Molence 50-pc 2.54 mm screw-terminal kit (part 267) into F0-R1C2, 2026-11-02.

Box label: Amazon FNSKU X003046YEF, "Molence 50PCS 2.54mm 0... V 6A for 26-18AWG
Cable". Scott: unused. Recorded as ONE kit unit on the kit part, not split into
the per-position parts (39/822/823) the opened SLN kit was counted into: the
2P/3P/4P mix of a sealed box is not counted, and a guessed split would be an
invented count. When it is opened, count it into those parts.

F0 because the box is wider than an F1 cell. 267's default_location was SLN
B3-R5C2, the solenoid drawer: a misfile, no 267 stock was ever there (the SLN
kit lives on as 39/822/823 in A3-R8C6). This row is 267's only stock, so
F0-R1C2 becomes the default. (The dry run read a truncated line and this
docstring first said "no default"; corrected after the run.) No PO line exists for
supplier part 167, so no price is set.

    itq run scripts/molence_kit_lrd_1102.py [--commit]
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

p = Part.objects.get(pk=267)
assert p.description.startswith("orig: Molence 50PCS 2.54mm"), p.description
assert not StockItem.objects.filter(part=p).exists(), "267 has stock now - merge, don't add"
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F0/F0-R1C2")
held = StockItem.objects.filter(location=loc)
assert not held.exists(), f"F0-R1C2 already holds {list(held.values_list('pk', 'part__name'))}"
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
print(f"part 267 x1 kit -> {loc.pathstring}; default {p.default_location} -> F0-R1C2")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

Part.objects.filter(pk=267).update(default_location=loc)
s = StockItem(part=p, location=loc, quantity=1)
s.save()
Note.objects.create(content_object=s, title="Source", primary=True, content=(
    "ONE unopened kit (Scott: unused), Amazon FNSKU X003046YEF, 2026-11-02. Label says 50 pcs of "
    "2P/3P/4P; the split per position is not counted. When opened, count into parts 39/822/823 "
    "(as the SLN kit was) and consume this row. No price on record."))
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 1.0}, notes="Into F0-R1C2, unopened.")

# Verify by re-read: .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=s.pk)
p.refresh_from_db()
print(f"stock {s.pk}: part 267 x{s.quantity:g} @ {s.location.pathstring}; default {p.default_location.pathstring}")
ok = s.quantity == 1 and s.location_id == loc.pk and s.notes.exists() and p.default_location_id == loc.pk
print("ALL VERIFIED" if ok else "NOT VERIFIED")
