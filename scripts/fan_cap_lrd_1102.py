"""Enter 1 Podoy CBB61 ceiling-fan capacitor (part 427) into F1-R3C4; retire duplicate part 7, 2026-11-02.

Bag label: Amazon FNSKU X001TOQVTV, "Podoy Ceiling Fa..C (Pack of 2)", K1227*2.
One left of the pair (Scott).

- Parts 7 and 427 are the same product (CBB61, 5-wire, 4.5+5+6 uF 250 VAC, pack
  of 2), neither held stock. 427 survives: it carries the Amazon supplier part
  (B071KKSBTC) and the full vendor title. 7 is the CSV-seed record; deactivated
  with a note, same pattern as 22/362. Not hard-merged: nothing hangs off 7.
- Supplier part 330 had pack_quantity 1 for a pack of 2. Written through .save()
  so pack_quantity_native follows (TRAPS: .update() changes only the text).
- Purchase history says last ordered 2025-04-27; no PO line carries a price, so
  none is set. 427's default was the bare LRD root, which is no home.

    itq run scripts/fan_cap_lrd_1102.py [--commit]
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

keep, dup = Part.objects.get(pk=427), Part.objects.get(pk=7)
assert keep.name.startswith("Podoy Ceiling Fan Capacitor") and dup.name.startswith("Podoy Ceiling Fan Capacitor")
assert not StockItem.objects.filter(part__in=[keep, dup]).exists(), "stock exists now - re-check before adding"
assert not SupplierPart.objects.filter(part=dup).exists(), "7 has supplier parts - needs a real merge"
sp = SupplierPart.objects.get(pk=330)
assert sp.part_id == 427 and sp.SKU == "B071KKSBTC", (sp.part_id, sp.SKU)
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R3C4")
held = StockItem.objects.filter(location=loc)
assert not held.exists(), f"F1-R3C4 already holds {list(held.values_list('pk', 'part__name'))}"
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
print(f"part 7 active {dup.active} -> False; SP 330 pack {sp.pack_quantity}/{sp.pack_quantity_native} -> 2")
print(f"part 427 x1 -> {loc.pathstring}; default {keep.default_location} -> F1-R3C4")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

Part.objects.filter(pk=7).update(active=False, description="DUPLICATE of #427. " + (dup.description or ""))
Note.objects.create(content_object=dup, title="Note", content=(
    "<p>Deactivated 2026-11-02 as a duplicate of part #427 (Podoy CBB61 fan capacitor). Same product "
    "recorded twice: once by the early CSV seed, once by the Amazon import with the full vendor title. "
    "Stock is recorded on 427.</p>"))
sp.pack_quantity = "2"
sp.save()
Part.objects.filter(pk=427).update(default_location=loc)
s = StockItem(part=keep, location=loc, quantity=1)
s.save()
Note.objects.create(content_object=s, title="Source", primary=True, content=(
    "Counted by Scott at put-away, 2026-11-02: 1 left of an Amazon 2-pack (bag FNSKU X001TOQVTV, "
    "K1227*2). Purchase history: last ordered 2025-04-27; no price on record, so none is set."))
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 1.0}, notes="Into F1-R3C4.")

# Verify by re-read: .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=s.pk)
keep.refresh_from_db(); dup.refresh_from_db(); sp.refresh_from_db()
print(f"stock {s.pk}: part {s.part_id} x{s.quantity:g} @ {s.location.pathstring}")
print(f"part 7 active {dup.active}; 427 default {keep.default_location}; SP 330 pack {sp.pack_quantity}/{sp.pack_quantity_native}")
ok = (s.quantity == 1 and s.location_id == loc.pk and s.notes.exists() and not dup.active
      and keep.default_location_id == loc.pk and float(sp.pack_quantity_native) == 2)
print("ALL VERIFIED" if ok else "NOT VERIFIED")
