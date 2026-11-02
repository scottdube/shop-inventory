"""Enter LMC662CN op-amps (F1-R3C3) and binding-post pairs (F1-R5C8) at LRD, 2026-11-02.

- LMC662CN x9: National dual CMOS op-amp, DIP-8, identified from the marks on
  the chip (NS logo, LMC 662CN, date code JM49AN). No part existed, so one is
  created next to "IC LM358 Op-Amp" (703) in Electronics/Semiconductors/ICs,
  named the same way. Source is the HOT club swap meet in Florida (Scott), so
  the price is $0. Count 9 from Scott.
- Binding post pairs x3: part 733 already existed, with no stock anywhere. Its
  only purchase record is AliExpress 2021-01-12 (5 pairs, $1.21 each). These 3
  are probably from that order, but that isn't established, so the note says
  so and the price is left unset rather than borrowed from the order. Count 3
  from Scott.

    itq run scripts/lmc662_binding_posts_lrd_1102.py [--commit]
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
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

F1 = "LRD/Akro Bins/F1/"
c3 = StockLocation.objects.get(pathstring=F1 + "F1-R3C3")
c8 = StockLocation.objects.get(pathstring=F1 + "F1-R5C8")
ics = PartCategory.objects.get(pathstring="Electronics/Semiconductors/ICs")
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
bp = Part.objects.get(pk=733)
assert bp.name.startswith("Binding Post Terminal Pair"), bp.name
assert not StockItem.objects.filter(part=bp).exists(), "733 has stock now - merge, don't add"
for loc in (c3, c8):
    held = StockItem.objects.filter(location=loc)
    assert not held.exists(), f"{loc.name} already holds {list(held.values_list('pk', 'part__name'))}"
dup = list(Part.objects.filter(name__icontains="LMC662"))
assert len(dup) <= 1, dup
print(f"LMC662CN x9 -> {c3.pathstring} ({'reuse part ' + str(dup[0].pk) if dup else 'new part'})")
print(f"part 733 x3 -> {c8.pathstring}; default_location now {bp.default_location}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

lmc = dup[0] if dup else Part.objects.create(
    name="IC LMC662CN Dual CMOS Op-Amp (DIP-8)", category=ics, component=True, purchaseable=True,
    description="National LMC662CN dual CMOS op-amp, rail-to-rail output, DIP-8. Marked LMC 662CN, date code JM49AN.",
    default_location=c3)
bp.default_location = c8
bp.save()

rows = []
for part, loc, qty, price, note in (
    (lmc, c3, 9, Money(0, "USD"),
     "Counted by Scott at put-away, 2026-11-02. HOT club swap meet, Florida, $0."),
    (bp, c8, 3, None,
     "Counted by Scott at put-away, 2026-11-02 (3 pairs). Probably from AliExpress order "
     "8124403479835753 (2021-01-12, 5 pairs at $1.21), the part's only purchase record; "
     "not established, so no price is set."),
):
    s = StockItem(part=part, location=loc, quantity=qty, purchase_price=price)
    s.save()
    Note.objects.create(content_object=s, title="Source", content=note, primary=True)
    s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": float(qty)}, notes=f"Into {loc.name}.")
    rows.append((s.pk, part.pk, loc.pk, qty))

# Verify by re-read: .save() on this install has reported success and written nothing.
bad = []
for pk, part_pk, loc_pk, qty in rows:
    s = StockItem.objects.get(pk=pk)
    p = Part.objects.get(pk=part_pk)
    print(f"stock {s.pk}: part {p.pk} {p.name} x{s.quantity:g} @ {s.location.pathstring} price {s.purchase_price}")
    if s.quantity != qty or s.location_id != loc_pk or not s.notes.exists() or p.default_location_id != loc_pk:
        bad.append(pk)
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
