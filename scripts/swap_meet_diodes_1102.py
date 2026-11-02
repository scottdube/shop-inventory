"""Enter the HOT swap-meet diodes at LRD, both in F1-R3C2 (2026-11-02).

Scott brought two bags back from the HOT club swap meet at no cost:
- 1N4001: the part exists (697, from the SparkFun kit, 5 at SLN B3-R2C4). This
  is a new row of it at LRD. "50" is hand-written on the bag, so the quantity
  is bag-stated, an [ESTIMATE], not a count.
- 1N4935: no part existed, so one is created next to 697 in
  Electronics/Semiconductors/Diodes. Quantity comes from Scott (--n4935).

Both share one drawer because Scott said both fit (F1 is one kind per drawer, and
diodes count as one kind). Price $0 because they cost nothing: a $0 row is the
truth and keeps them out of any valuation, unlike leaving the price unset.

    itq run scripts/swap_meet_diodes_1102.py --n4935 N [--commit]
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from djmoney.money import Money  # noqa: E402
from InvenTree.status_codes import StockHistoryCode  # noqa: E402
from common.models import Note  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--n4935", type=int, required=True)
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

SRC = "HOT club swap meet, $0 (Scott, 2026-11-02)."
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R3C2")
cat = PartCategory.objects.get(pathstring="Electronics/Semiconductors/Diodes")
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
p4001 = Part.objects.get(pk=697)
assert p4001.name == "Diode 1N4001", p4001.name
# The first --commit created the part, then died on notes= (see below), so reuse it.
dup = list(Part.objects.filter(name__icontains="4935"))
assert len(dup) <= 1 and all(d.name == "Diode 1N4935" for d in dup), dup
held = StockItem.objects.filter(location=loc)
assert not held.exists(), f"F1-R3C2 already holds {list(held.values_list('pk', 'part__name'))}"
print(f"F1-R3C2 empty; 1N4001 rows now: "
      f"{[(s.pk, s.quantity, s.location.pathstring) for s in StockItem.objects.filter(part=p4001)]}")
print(f"would add 1N4001 x50 [ESTIMATE] and new part 1N4935 x{a.n4935} at {loc.pathstring}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

p4935 = dup[0] if dup else Part(name="Diode 1N4935", category=cat, component=True, purchaseable=True,
             description="Fast-recovery rectifier, 1 A, 200 V, DO-41 axial (on tape strips)",
             default_location=loc)
if not dup:
    p4935.save()

rows = []
for part, qty, note in (
    (p4001, 50, f"[ESTIMATE] 50 is hand-written on the swap-meet bag, not counted. {SRC}"),
    (p4935, a.n4935, f"Count from Scott at put-away. {SRC}"),
):
    # notes is a read-only property on 1.6 (common.Note rows); notes= in the
    # constructor raises. The older scripts that pass notes= predate the upgrade.
    s = StockItem(part=part, location=loc, quantity=qty, purchase_price=Money(0, "USD"))
    s.save()
    Note.objects.create(content_object=s, title="Source", content=note, primary=True)
    s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": float(qty)},
                         notes=f"Into F1-R3C2. {SRC}")
    rows.append((s.pk, part.pk, qty))

# Verify by re-read: .save() on this install has reported success and written nothing.
bad = []
for pk, part_pk, qty in rows:
    s = StockItem.objects.get(pk=pk)
    print(f"stock {s.pk}: {s.part.name} x{s.quantity:g} @ {s.location.pathstring} "
          f"price {s.purchase_price} | {[n.content[:40] for n in s.notes]}")
    if s.part_id != part_pk or s.quantity != qty or s.location_id != loc.pk or s.purchase_price != Money(0, "USD") \
            or not s.notes.exists():
        bad.append(pk)
p = Part.objects.get(pk=p4935.pk)
if p.default_location_id != loc.pk or p.category_id != cat.pk:
    bad.append(f"part {p.pk}")
print(f"new part {p.pk} {p.name}")
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
