"""Add the 30203 tapered roller bearings: 2 sets, off the bag label.

Bag 2026-08-26: "X00AQ4ZHV / 2 Sets 30203 Taped Roller Bearing 17x40x12mm /
New". ("Taped" is the seller's typo for TAPERED.)

NOT run through add_bearing.py. That script builds deep-groove BALL bearings
and would have named this one, which is the kind of wrong that looks right.

A "SET" IS THE UNIT, and it is the whole reason this part is not counted in
pieces. A tapered roller bearing ships as a matched CONE (inner ring + roller
cage) and CUP (outer race). They are lapped together and are not
interchangeable between sets -- a cone from one set in a cup from another is a
scrap bearing that will appear to assemble fine. So 2 sets = 2 cones + 2 cups,
counted as 2, and splitting the row would be a real error rather than a
bookkeeping preference.

WIDTH: the label's "12mm" is the cone width B. The 30203 standard OVERALL width
T is 13.25mm, and T is the number that matters when a housing is being
machined. Both recorded; neither measured.
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
NAME = "Tapered Roller Bearing 30203, 17 x 40 mm, cone + cup set"
DESC = ("Tapered roller bearing, 30203 -- 17 mm bore, 40 mm OD. Matched cone "
        "and cup, sold and counted as a SET. Takes combined radial and axial "
        "load in one direction.")
NOTES = (
    "BORE 17.000 mm · OD 40.000 mm · WIDTH 13.250 mm\n\n"
    "COUNTED IN SETS, NOT PIECES. Cone (inner ring + rollers) and cup (outer "
    "race) are lapped as a pair. A cone from one set in a cup from another "
    "assembles perfectly and is a scrap bearing. Never split this row.\n\n"
    "WIDTH: the bag says 17x40x12mm. 12 mm is the cone width B; the 30203 "
    "standard OVERALL width T is 13.25 mm. T is what a housing has to be cut "
    "for. Neither figure is measured -- both come off the label and the "
    "standard.\n\n"
    "NOT A DROP-IN FOR THE 6203RS (#1121), WHICH IS ALSO 17 x 40. Same bore, "
    "same OD, different bearing entirely:\n"
    "  - Tapered rollers carry combined radial + THRUST load, in ONE direction. "
    "They are normally fitted in opposed pairs.\n"
    "  - They must be PRELOADED or set with endplay on assembly. A deep-groove "
    "ball bearing is pressed in and forgotten.\n"
    "  - Run one unpreloaded, or singly where thrust reverses, and it fails.\n"
    "This is the most dangerous pair in the bin precisely because the envelope "
    "matches: it will go in where the 6203 goes.\n\n"
    "Bag label X00AQ4ZHV, marked New. No purchase order in this system matches "
    "it; vendor and date unknown, so none is claimed.")
STOCK_NOTE = (
    "[ESTIMATE] Quantity 2 is the LABEL figure ('2 Sets'), read 2026-08-26. "
    "Nobody counted it and no stocktake_date is set.\n\n"
    "The bag reads as sealed and marked New, so 2 is probably right -- but the "
    "LM8UU bag the same afternoon said 12 and held 10. A printed pack count is "
    "not a count. Confirm when the bin is loaded: 2 sets means TWO CONES AND "
    "TWO CUPS, four pieces in the bag.")

print("duplicate guard:")
for p in Part.objects.filter(name__icontains="30203") | Part.objects.filter(name__icontains="tapered"):
    print(f"  [{p.pk}] {p.name}")
print(f"seed: 2 sets x {NAME}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

binloc = StockLocation.objects.get(pk=BIN)
p = Part.objects.filter(name=NAME).first()
if not p:
    p = Part.objects.create(name=NAME, description=DESC, category_id=CAT,
                            default_location=binloc,
                            purchaseable=True, active=True)
    print(f"part [{p.pk}] created")
# units="set" is REJECTED -- InvenTree validates `units` against a physical
# unit registry (mm, g, A...), and a set is a packaging fact, not a dimension.
# The unit lives in the part NAME instead, where it is visible on every label
# and in every search result rather than in a field nobody renders.
Part.objects.filter(pk=p.pk).update(notes=NOTES, default_location=binloc)

si = StockItem.objects.filter(part=p, location=binloc).first()
if not si:
    si = StockItem.objects.create(part=p, location=binloc, quantity=2)
StockItem.objects.filter(pk=si.pk).update(notes=STOCK_NOTE)

# mutual warning on the 6203, which is the part someone will actually reach for
ball = Part.objects.get(pk=1121)
tagline = (f"\n\nSAME 17 x 40 ENVELOPE, COMPLETELY DIFFERENT BEARING — "
           f"{NAME} (#{p.pk}) shares this bore AND this OD. It is a TAPERED "
           f"ROLLER: it carries thrust in one direction, wants an opposed pair, "
           f"and must be preloaded on assembly. It will physically fit wherever "
           f"this ball bearing fits. That is the hazard, not the convenience.")
if f"(#{p.pk})" not in (ball.notes or ""):
    Part.objects.filter(pk=1121).update(notes=(ball.notes or "").rstrip() + tagline)

si.refresh_from_db()
print(f"[{p.pk}] stock[{si.pk}] qty={si.quantity:g} sets, stocktake={si.stocktake_date}")
