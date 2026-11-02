"""Enter two kinds of panel knob found loose at LRD, both in F1-R4C2 (2026-11-02).

No knob part existed. The only "knob" rows were pots sold with knobs (10, 444) and
BT30 pull studs. Two new parts go in Electromechanical, the same flat root the
battery contacts went into. Counts are Scott's from put-away (9 and 5), so they
are tallied, not estimates. The bore isn't visible in the photos and isn't
recorded. Source: SLN stock that was never inventoried (Scott). Price is left unset, not $0: $0 would
claim they were free, and there is no PO to price them from.

R4 is switches/controls, and C2 sits next to the toggles in C1. Both kinds share
one drawer (knobs are one kind), as the two diodes do in R3C2.

    itq run scripts/knobs_lrd_1102.py [--commit]
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
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

KNOBS = [  # name, description, qty
    ("Knob, plastic, black with blue pointer cap",
     "Panel/pot knob, black ribbed plastic body with blue pointer insert on top. Bore not recorded.", 9),
    ("Knob, aluminum, black knurled",
     "Panel/pot knob, black anodized aluminum, knurled skirt, engraved pointer line. Bore not recorded.", 5),
]

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R4C2")
cat = PartCategory.objects.get(pathstring="Electromechanical")
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
held = StockItem.objects.filter(location=loc)
assert not held.exists(), f"F1-R4C2 already holds {list(held.values_list('pk', 'part__name'))}"
for name, _, qty in KNOBS:
    dup = Part.objects.filter(name=name)
    assert dup.count() <= 1, list(dup)
    print(f"{'reuse' if dup else 'new'} part '{name}' x{qty} -> {loc.pathstring}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

rows = []
for name, desc, qty in KNOBS:
    p = Part.objects.filter(name=name).first() or Part.objects.create(
        name=name, description=desc, category=cat, component=True, purchaseable=True, default_location=loc)
    s = StockItem(part=p, location=loc, quantity=qty)
    s.save()
    Note.objects.create(content_object=s, title="Source", primary=True,
                        content="Counted by Scott at put-away, 2026-11-02. Came from SLN stock that was never in inventory; no PO or price.")
    s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": float(qty)}, notes="Into F1-R4C2.")
    rows.append((s.pk, p.pk, qty))

# Verify by re-read: .save() on this install has reported success and written nothing.
bad = []
for pk, part_pk, qty in rows:
    s = StockItem.objects.get(pk=pk)
    p = Part.objects.get(pk=part_pk)
    print(f"stock {s.pk}: part {p.pk} {p.name} x{s.quantity:g} @ {s.location.pathstring}")
    if s.quantity != qty or s.location_id != loc.pk or not s.notes.exists() \
            or p.default_location_id != loc.pk or p.category_id != cat.pk:
        bad.append(pk)
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
