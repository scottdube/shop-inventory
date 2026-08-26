"""Add the 608ZZ ball bearings: 13, counted by Scott 2026-08-26.

A SEPARATE part from the 608RS (#1119), not a variant of the same row. Same
8 x 22 x 7 envelope, different closure, and the closure is the whole reason to
reach for one over the other:

  ZZ  metal shields  -- lower drag, higher speed, no rubbing seal. Keeps chips
                        out, does not keep grease in or fine grit out.
  RS  rubber seals   -- better sealing, more drag, lower speed ceiling.

Merging them would put 62 bearings on one row and make the choice invisible at
exactly the moment somebody is choosing.
"""
import argparse, os, sys, django, datetime

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

BIN, CAT = 587, 137
NAME = "Ball Bearing 608ZZ, 8 x 22 x 7 mm"
DESC = ("Deep-groove radial ball bearing, 608 series -- 8 mm bore, 22 mm OD, "
        "7 mm wide, METAL SHIELDED (ZZ). Non-contact shields: lower drag and "
        "higher speed than the sealed RS.")
NOTES = (
    "NOT interchangeable with the 608RS (#1119) despite an identical envelope. "
    "ZZ shields do not touch the inner race -- less friction, more speed, but "
    "they do not retain grease or exclude fine grit the way a rubber seal does. "
    "Pick ZZ for a spinning idler, RS for anything dusty or washed down.\n\n"
    "Also shares an 8 mm bore with the LM8UU bushings in this bin and is not "
    "related to them at all: 608 spins on the shaft, LM8UU slides along it.\n\n"
    "No purchase order in this system matches these; vendor and date unknown.")
STOCK_NOTE = "TALLIED 2026-08-26. Scott counted 13 in hand."

print("existing 608 parts:")
for p in Part.objects.filter(name__icontains="608"):
    q = sum(float(s.quantity) for s in StockItem.objects.filter(part=p))
    print(f"  [{p.pk}] {q:g} x {p.name}")
binloc = StockLocation.objects.get(pk=BIN)
print(f"seed: 13 x {NAME}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

p = Part.objects.filter(name=NAME).first()
if not p:
    p = Part.objects.create(name=NAME, description=DESC, category_id=CAT,
                            default_location=binloc, purchaseable=True, active=True)
    print(f"part [{p.pk}]")
Part.objects.filter(pk=p.pk).update(notes=NOTES, default_location=binloc)

si = StockItem.objects.filter(part=p, location=binloc).first()
if not si:
    si = StockItem.objects.create(part=p, location=binloc, quantity=13)
StockItem.objects.filter(pk=si.pk).update(
    notes=STOCK_NOTE, stocktake_date=datetime.date(2026, 8, 26))

# cross-reference the RS row so the pair is discoverable from either side
rs = Part.objects.get(pk=1119)
if "608ZZ" not in (rs.notes or ""):
    Part.objects.filter(pk=1119).update(notes=(rs.notes or "").rstrip() +
        f"\n\nSEE ALSO the 608ZZ (#{p.pk}) in this same bin: identical "
        f"8 x 22 x 7 envelope, metal shields instead of rubber seals. Lower "
        f"drag and higher speed, worse at keeping grit out.")

si.refresh_from_db()
print(f"\n[{p.pk}] stock[{si.pk}] qty={si.quantity:g} stocktake={si.stocktake_date}")
print("\n608 family in the bin:")
for q in Part.objects.filter(name__icontains="608").order_by("name"):
    tot = sum(float(s.quantity) for s in StockItem.objects.filter(part=q))
    print(f"  [{q.pk}] {tot:>3g} x {q.name}")
