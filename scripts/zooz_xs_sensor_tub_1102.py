"""Enter a Zooz ZSE41 XS open/close sensor and its waterproof case into the new Smart Switches & Plugs tub, 2026-11-02.

Identified from the boxes: "open | close xs sensor, ZSE41 800LR, ZOOZ" and
"waterproof case for xs sensor, ZOOZ". Neither had a part (searched ZSE41,
"XS sensor", "open/close", "waterproof case"), so both are created in Modules
beside the other Zooz devices (423, 386, 376). Scott: "Tub" in answer to the
proposal of the Smart switches & plugs tub, 1 of each, so 1 of each.

The tub is STORAGE-PLAN.md's "Smart switches & plugs" tub: Z-Wave devices waiting
to be deployed. No tub had a location yet. It is made under LRD/Countertop Wall,
not under a shelf, because tub placement is not settled (Scott, 2026-11-01); it
moves to its shelf when that is decided. Named for what it holds, not where.
The Athom plugs (stock 1096, in Receiving) belong in this tub per the plan, but
Scott has not said they are in it, so they are not moved here.

Source not stated, so no price.

    itq run scripts/zooz_xs_sensor_tub_1102.py [--commit]
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
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

TUB = "Smart Switches & Plugs Tub"
wall = StockLocation.objects.get(pathstring="LRD/Countertop Wall")
cat = Part.objects.get(pk=423).category
assert cat.pathstring == "Modules", cat.pathstring
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
assert not StockLocation.objects.filter(name__icontains="Smart Switches").exists(), "tub location already exists"
dup = list(Part.objects.filter(Q(name__icontains="ZSE41") | Q(name__icontains="XS sensor")
                               | Q(name__icontains="open/close") | Q(name__icontains="open close sensor"))
           .values_list("pk", "name"))
assert not dup, dup

PARTS = [
    ("Zooz 800 Series Z-Wave Long Range XS Open/Close Sensor ZSE41 800LR",
     "Zooz ZSE41 800LR XS open/close (door/window) sensor, Z-Wave Long Range. Identified from the box."),
    ("Zooz Waterproof Case for XS Sensor",
     "Zooz waterproof case for the XS sensors (fits the ZSE41 open/close sensor). Identified from the box."),
]
print(f"new location: {wall.pathstring}/{TUB}")
for name, _ in PARTS:
    print(f"new part in {cat.pathstring}: {name}; x1 -> tub")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

tub = StockLocation.objects.create(
    name=TUB, parent=wall,
    description="Clear tub (STORAGE-PLAN 'Smart switches & plugs'): Z-Wave and smart-plug devices waiting "
                "to be deployed. Shelf not settled yet (2026-11-02); move this location to its Cab shelf when it is.")
rows = []
for name, desc in PARTS:
    p = Part.objects.create(name=name, description=desc, category=cat, component=True,
                            purchaseable=True, default_location=tub)
    s = StockItem(part=p, location=tub, quantity=1)
    s.save()
    Note.objects.create(content_object=s, title="Source", primary=True,
                        content="Found at LRD; put in the Smart Switches & Plugs tub by Scott, 2026-11-02 "
                                "(1, boxed). Source not stated.")
    s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 1.0}, notes=f"Into {TUB}.")
    rows.append((s.pk, p.pk))

# Verify by re-read: .save() on this install has reported success and written nothing.
tub = StockLocation.objects.get(pk=tub.pk)
print(f"location {tub.pk}: {tub.pathstring}")
bad = []
for spk, ppk in rows:
    s = StockItem.objects.get(pk=spk)
    p = Part.objects.get(pk=ppk)
    print(f"stock {s.pk}: part {p.pk} {p.name} x{s.quantity:g} @ {s.location.pathstring}")
    if s.quantity != 1 or s.location_id != tub.pk or p.default_location_id != tub.pk or not s.notes.exists():
        bad.append(spk)
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
