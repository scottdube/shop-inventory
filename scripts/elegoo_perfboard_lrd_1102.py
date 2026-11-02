"""Enter the ELEGOO double-sided perfboard kit (part 329) into F0-R1C1; retire duplicate part 81, 2026-11-02.

Scott: Amazon, last season. Purchase history: ELEGOO 32-pc, 5 sizes, B072Z7Y19F,
ordered 2026-03-15 (same day as the Nanos, 1192). Photo shows all five sizes
(7x9 x1, then stacks of 5x7, 4x6, 3x7, 2x8). Into F0-R1C1 with the copper
clad (285), Scott's cell: the 7x9 board needs F0.

- Recorded as ONE kit unit: an assortment, not a multipack (CLAUDE.md). The kit
  is open and the per-size counts were not given, so none are invented.
- 81 and 329 are the same Amazon kit, neither held stock. 329 survives: it
  carries the supplier part. It takes 81's short name and its Prototyping
  category (329 sat in Consumables/Solder, a seed misfile). 81 is deactivated
  with a note; nothing hangs off it.
- No price on record, so none is set. 329 had no default_location.

    itq run scripts/elegoo_perfboard_lrd_1102.py [--commit]
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
from company.models import SupplierPart  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

keep, dup = Part.objects.get(pk=329), Part.objects.get(pk=81)
assert dup.name == "ELEGOO Double Sided PCB Prototype Board Kit 5 sizes", dup.name
assert keep.description.startswith("orig: ELEGOO 32 Pcs Double Sided PCB"), keep.description
assert not StockItem.objects.filter(part__in=[keep, dup]).exists(), "stock exists now - re-check before adding"
assert not SupplierPart.objects.filter(part=dup).exists(), "81 has supplier parts - needs a real merge"
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F0/F0-R1C1")
held = list(StockItem.objects.filter(location=loc).values_list("pk", flat=True))
assert held == [285], f"F0-R1C1 holds {held}, expected only the copper clad (285)"
assert keep.default_location is None, keep.default_location
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
NAME, CAT = dup.name, dup.category
print(f"part 81 -> inactive; 329 name -> {NAME!r}; category {keep.category} -> {CAT}")
print(f"part 329 x1 kit -> {loc.pathstring}; default -> F0-R1C1")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

Part.objects.filter(pk=81).update(active=False, name=NAME + " [duplicate of #329]",
                                  description="DUPLICATE of #329. " + (dup.description or ""))
Note.objects.create(content_object=dup, title="Note", content=(
    "<p>Deactivated 2026-11-02 as a duplicate of part #329 (ELEGOO 32-pc double-sided perfboard kit). "
    "Same Amazon kit recorded twice: once by the early CSV seed, once by the Amazon import. Stock is "
    "recorded on 329, which took this part's name and category.</p>"))
Part.objects.filter(pk=329).update(name=NAME, category=CAT, default_location=loc)
s = StockItem(part=keep, location=loc, quantity=1)
s.save()
Note.objects.create(content_object=s, title="Source", primary=True, content=(
    "ONE kit unit, opened (Scott, 2026-11-02). Amazon B072Z7Y19F, ordered 2026-03-15 per purchase "
    "history; 32 pcs in 5 sizes as sold. Seen at put-away: 7x9 x1, plus stacks of 5x7, 4x6, 3x7 and "
    "2x8; per-size counts not taken. No price on record."))
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 1.0}, notes="Into F0-R1C1, with the copper clad.")

# Verify by re-read: .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=s.pk)
keep.refresh_from_db(); dup.refresh_from_db()
print(f"stock {s.pk}: part {s.part_id} {keep.name} x{s.quantity:g} @ {s.location.pathstring}")
print(f"329 cat {keep.category}; 81 active {dup.active}")
ok = (s.quantity == 1 and s.location_id == loc.pk and s.notes.exists() and not dup.active
      and keep.name == NAME and keep.category_id == CAT.pk and keep.default_location_id == loc.pk)
print("ALL VERIFIED" if ok else "NOT VERIFIED")
