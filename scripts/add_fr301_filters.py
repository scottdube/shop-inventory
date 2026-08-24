"""Create the FR-301 spare filter set and file it with the nozzles in A3-R1C2.

Scott, 2026-08-24: "this is also a spare that came with the gun that I will
store in the same place as the nozzles."

**Provenance is the interesting field here, and it is the one a purchase-history
importer can never supply.** This came in the box with the FR-301 (#474). It was
never separately ordered, so it will never appear on a PO, and any future sweep
that reconciles parts against orders should find it unmatched and NOT conclude
it was invented. Saying so on the record is the whole point.

Quantity is 1 SEALED SET, which is a real count of a physical object -- the same
move as the 15 m sleeve, where the countable thing was one coil and the length
was an attribute. What is in the bag (2 white filter pads + 1 metal holder) is
read off a photograph, so it is recorded as a DESCRIPTION and not as a quantity.
Photographs show identity, not counts.

No stocktake_date: nobody has opened the bag and counted its contents.

Hakko's own part number is NOT recorded because nobody verified it. A confident
wrong MPN is worse than a blank one -- it gets reordered.

    itq run scripts/add_fr301_filters.py
    itq run scripts/add_fr301_filters.py --commit
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part                       # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

NAME = "Hakko FR-301 Filter Set — pads + holder (spare, shipped with the gun)"
# Part.description is capped at 250 chars; Part.notes holds 50,000. The
# "name the problem, not the object" convention needs the TRIGGER in the
# description -- that is the field that shows in search results -- and the
# reasoning goes in notes where there is room for it.
DESC = ("Spare filter set shipped in the box with the FR-301 gun (#474). Reach "
        "for it when the gun stops pulling solder — a clogged filter looks "
        "exactly like a dead pump. Hakko P/N NOT VERIFIED; check the manual "
        "before reordering.")
NOTES = """## Provenance

Came in the box with the **FR-301 desoldering gun (#474)**. Never separately
ordered, so it sits on no purchase order *by design* — a sweep that reconciles
parts against orders should find this unmatched and must not read that as
evidence the record was invented.

## When you reach for it

The gun losing suction reads as a dead pump. It is usually the filter. Swap the
pad first, not last — running it clogged drives solder residue further into the
barrel, which is the expensive version of this problem.

## What is NOT known

Hakko's own part number. Nobody verified it, so nothing is recorded rather than
a plausible guess — a confident wrong MPN gets reordered, and the wrong filter
arrives looking correct.
"""
NOTE = ("One SEALED bag, counted as 1 set. Contents read from a photograph "
        "2026-08-24 — 2 white filter pads and 1 metal filter holder — and "
        "therefore NOT COUNTED: no stocktake_date until somebody opens the bag "
        "and looks. Provenance: shipped with the FR-301, not purchased "
        "separately (Scott, 2026-08-24).")
DRAWER = "A3-R1C2"

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

# Duplicate check. Two importers have already entered the same item twice.
dupes = Part.objects.filter(name__icontains="FR-301").exclude(pk=474)
print("existing FR-301 parts (excluding the gun #474):")
for p in dupes:
    print(f"   #{p.pk} active={p.active} {p.name[:60]}")
if dupes.filter(name__icontains="filter").exists():
    print("!! a FR-301 filter part already exists — refusing")
    raise SystemExit(1)

locs = list(StockLocation.objects.filter(name__iexact=DRAWER))
assert len(locs) == 1, f"{DRAWER} matched {len(locs)}"
loc = locs[0]
template = Part.objects.get(pk=213)     # the nozzle: same category, same drawer

print(f"\nCREATE  {NAME}")
print(f"        category  {template.category}")
print(f"        defloc    {loc.pathstring}")
print(f"        stock     1 set, no stocktake_date, at {loc.name}")

if not a.commit:
    print("\nDRY RUN — add --commit")
    raise SystemExit

assert len(DESC) <= 250, f"description is {len(DESC)} chars, limit is 250"
part = Part.objects.create(name=NAME, description=DESC, notes=NOTES,
                           category=template.category,
                           default_location=loc, active=True,
                           keywords=("fr-301, fr301, filter, filter pad, "
                                     "desoldering filter, hakko, no suction, "
                                     "clogged, spare"))
fresh = Part.objects.get(pk=part.pk)
assert fresh.name == NAME and fresh.default_location_id == loc.pk, "part did not stick"
assert fresh.notes and "Provenance" in fresh.notes, "notes did not stick"
print(f"\nOK  part #{fresh.pk} created")

si = StockItem.objects.create(part=fresh, location=loc, quantity=1, notes=NOTE)
chk = StockItem.objects.get(pk=si.pk)
assert float(chk.quantity) == 1 and chk.location_id == loc.pk, "stock did not stick"
assert chk.stocktake_date is None, "something stamped a stocktake date"
print(f"OK  stock #{chk.pk} qty=1 set at {chk.location.pathstring}, "
      f"stocktake={chk.stocktake_date}")
