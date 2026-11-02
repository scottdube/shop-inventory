"""Enter 2 MAX98357A I2S amp breakouts (part 22) into F1-R2C6, beside the INMP441, 2026-11-02.

Scott put them in R2C6 with the INMP441 mic (1220), not the proposed R2C7: the
I2S audio pair share a cell. Identified from the silkscreen (purple board,
"MAX 98357A I2S Amp"), each with its 7-pin header and 2-pin terminal block.

Part 22 was inactive: first deactivated as a duplicate of 362, then 362 was
merged INTO 22 and nobody reactivated it (docs/TRAPS.md). It is the survivor:
it holds stock 279 and the Voice Assistant BOM line. Reactivated here, and the
stale "DUPLICATE of #362." prefix is dropped from its description. A new row
rather than merging into 279, because 279 is the voice-assistant kit's amp in
another location.

Probably from Amazon 2026-04-06 (DaFuRui 5-pack), the part's only purchase
record; not established, so no price. default_location was None; R2C6 is
where spares now live.

    itq run scripts/max98357_lrd_1102.py [--commit]
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

PREFIX = "DUPLICATE of #362. "
p = Part.objects.get(pk=22)
assert p.name.startswith("MAX98357"), p.name
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R2C6")
held = list(StockItem.objects.filter(location=loc).values_list("part_id", flat=True))
assert held == [55], f"F1-R2C6 holds parts {held}, expected only the INMP441 (55)"
assert not StockItem.objects.filter(part=p, location=loc).exists(), "already a row here - merge"
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
desc = p.description[len(PREFIX):] if p.description.startswith(PREFIX) else p.description
print(f"part 22 active {p.active} -> True; desc -> {desc!r}")
print(f"part 22 x2 -> {loc.pathstring}; default {p.default_location} -> F1-R2C6")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

Part.objects.filter(pk=22).update(active=True, description=desc, default_location=loc)
Note.objects.create(content_object=p, title="Reactivated", content=(
    "Reactivated 2026-11-02: part 362 was merged into this one, so this is the survivor "
    "(holds stock 279 and the Voice Assistant BOM line). The earlier 'duplicate of #362' "
    "deactivation predates that merge."))
s = StockItem(part=p, location=loc, quantity=2)
s.save()
Note.objects.create(content_object=s, title="Source", primary=True, content=(
    "Found at LRD; counted by Scott at put-away, 2026-11-02 (2, each with header and terminal block). "
    "Probably from Amazon 2026-04-06 (DaFuRui 5-pack), the part's only purchase record; "
    "not established, so no price is set."))
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 2.0}, notes="Into F1-R2C6, with the INMP441.")

# Verify by re-read: .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=s.pk)
p.refresh_from_db()
print(f"stock {s.pk}: {p.name} x{s.quantity:g} @ {s.location.pathstring}")
print(f"part 22 active {p.active}; default {p.default_location.pathstring}; desc {p.description[:60]!r}")
ok = (s.quantity == 2 and s.location_id == loc.pk and s.notes.exists() and p.active
      and p.default_location_id == loc.pk and not p.description.startswith("DUPLICATE"))
print("ALL VERIFIED" if ok else "NOT VERIFIED")
