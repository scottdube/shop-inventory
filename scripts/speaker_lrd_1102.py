"""Enter 3 D-FLIFE 3 W 8 ohm mini speakers (part 185) into F1-R2C8; retire duplicate part 51, 2026-11-02.

Scott's cell (R2C8, with the modules) over the proposed F0-R1C2. Identified
from the photo: boxed mini speaker, mounting ears, red/black lead to a JST-PH2.0
plug, matching the D-FLIFE listing. Count 3 from Scott.

- 51 and 185 are the same Amazon 6-pack, neither held stock. 185 survives: it
  carries the supplier part (B0C6F9RGXF). It takes 51's short name and its
  Electromechanical category (185 sat in Connectors, a seed misfile). 51 is
  deactivated with a note; nothing hangs off it, so no hard merge.
- Supplier part 85 had pack_quantity 1 for a pack of 6; written via .save() so
  pack_quantity_native follows.
- Purchase history: last ordered 2026-02-12; no PO line carries a price, so none
  is set. 185's default was the bare LRD root, which is no home.

    itq run scripts/speaker_lrd_1102.py [--commit]
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

keep, dup = Part.objects.get(pk=185), Part.objects.get(pk=51)
assert dup.name == "D-FLIFE Mini Speaker 3W 8ohm w/ JST-PH2.0", dup.name
assert keep.description.startswith("orig: D-FLIFE 6pcs Speaker 3 Watt 8 Ohm"), keep.description
assert not StockItem.objects.filter(part__in=[keep, dup]).exists(), "stock exists now - re-check before adding"
assert not SupplierPart.objects.filter(part=dup).exists(), "51 has supplier parts - needs a real merge"
sp = SupplierPart.objects.get(pk=85)
assert sp.part_id == 185 and sp.SKU == "B0C6F9RGXF", (sp.part_id, sp.SKU)
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R2C8")
held = StockItem.objects.filter(location=loc)
assert not held.exists(), f"F1-R2C8 already holds {list(held.values_list('pk', 'part__name'))}"
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
NAME, CAT = dup.name, dup.category
print(f"part 51 -> inactive; 185 name {keep.name[:40]!r} -> {NAME!r}; category {keep.category} -> {CAT}")
print(f"SP 85 pack {sp.pack_quantity} -> 6; part 185 x3 -> {loc.pathstring}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

Part.objects.filter(pk=51).update(active=False, name=NAME + " [duplicate of #185]",
                                  description="DUPLICATE of #185. " + (dup.description or ""))
Note.objects.create(content_object=dup, title="Note", content=(
    "<p>Deactivated 2026-11-02 as a duplicate of part #185 (D-FLIFE 3 W 8 ohm mini speaker, JST-PH2.0). "
    "Same Amazon 6-pack recorded twice: once by the early CSV seed, once by the Amazon import. "
    "Stock is recorded on 185, which took this part's name and category.</p>"))
Part.objects.filter(pk=185).update(name=NAME, category=CAT, default_location=loc)
sp.pack_quantity = "6"
sp.save()
s = StockItem(part=keep, location=loc, quantity=3)
s.save()
Note.objects.create(content_object=s, title="Source", primary=True, content=(
    "Counted by Scott at put-away, 2026-11-02: 3 of an Amazon 6-pack (D-FLIFE, B0C6F9RGXF). "
    "Purchase history: last ordered 2026-02-12; no price on record, so none is set."))
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 3.0}, notes="Into F1-R2C8.")

# Verify by re-read: .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=s.pk)
keep.refresh_from_db(); dup.refresh_from_db(); sp.refresh_from_db()
print(f"stock {s.pk}: part {s.part_id} {keep.name} x{s.quantity:g} @ {s.location.pathstring}")
print(f"185 cat {keep.category}; 51 active {dup.active} {dup.name!r}; SP 85 pack {sp.pack_quantity}/{sp.pack_quantity_native}")
ok = (s.quantity == 3 and s.location_id == loc.pk and s.notes.exists() and not dup.active
      and keep.name == NAME and keep.category_id == CAT.pk and keep.default_location_id == loc.pk
      and float(sp.pack_quantity_native) == 6)
print("ALL VERIFIED" if ok else "NOT VERIFIED")
