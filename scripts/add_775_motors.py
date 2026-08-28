"""Catalogue the two 775 DC motors with brackets. Bench stock, no known project.

Label: "775 DC Motor DC 12V ... Motor (With bracket)", ASIN X002PW3B7B, Made in
China. Not in the catalogue, no supplier part carries the ASIN, no PO matches —
another purchase that was invisible until the box turned up.

NOT the cord retraction system. That inference was made and corrected by Scott
2026-08-28: "the idea was to make them spring loaded... they're pulling back
voltage leads, very lightweight. So, no, they weren't motorized." Recorded on
RB-08 so nobody re-derives it. These motors have no known owner and are filed
as ordinary bench stock with no origin tag, unlike the X27s.

    itq run scripts/add_775_motors.py            # dry run
    itq run scripts/add_775_motors.py --commit
"""
import argparse, datetime, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory                       # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

BIN, QTY = "B2-R5C1", 2
TODAY = datetime.date.today()
NAME = "775 DC Motor, 12V brushed, with mounting bracket"
DESC = ("775-frame brushed DC motor, 12V nominal, 5mm shaft, supplied with an "
        "L-bracket. ASIN X002PW3B7B. 775 is a can size, not a model — windings "
        "vary between sellers and this one's are unmeasured.")
NOTES = (
 f"TALLIED {TODAY}: Scott counted two, each with its bracket.\n\n"
 "775 IS A CAN SIZE, NOT A PART NUMBER. It names the frame — nominally 42 mm "
 "diameter by 66 mm body, 5 mm shaft — and nothing else. Sellers wind them for "
 "anything from 12 V to 24 V with wildly different speed and torque constants, "
 "so datasheet figures found online for 'a 775' describe somebody else's motor. "
 "Measure this one before designing around it.\n\n"
 "STALL CURRENT EXCEEDS THE PWM CONTROLLERS IN B3-R5C4. A 775 on 12 V draws "
 "roughly an amp free-running and a few amps working, but stalled it will pull "
 "well past 10 A — and #1138 is fused at exactly 10 A with no current limit and "
 "no soft-start. Pairing them is fine and they are a natural pair, but a jam "
 "blows the fuse rather than backing off, and inrush at switch-on may nuisance-"
 "trip it too. That is the fuse doing its job; it is not a fault.\n\n"
 "NO KNOWN PROJECT. Bench stock. The cord retraction system was considered and "
 "ruled out by Scott 2026-08-28 — that design is spring-loaded, not motorised. "
 "No origin tag is set because none is known; an unsupported guess in metadata "
 "is worse than an empty field.\n\n"
 "No purchase order or supplier part in this system matches the ASIN; vendor and "
 "date unknown, so none is claimed.")
BINDESC = ("MOTORS — 775-frame brushed DC, on their brackets. A LARGE drawer by "
           "necessity: the can alone is 42 x 66 mm and the bracket adds to it. "
           "The B3 motor row was full, which is the only reason these are on B2. "
           "[6 x 4-9/16 x 2-3/16 in, large]")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

locs = list(StockLocation.objects.filter(name__iexact=BIN))
if len(locs) != 1:
    sys.exit(f"!! {BIN} matched {len(locs)}")
loc = locs[0]
if StockItem.objects.filter(location=loc).exists():
    sys.exit(f"!! {BIN} is not empty")
if Part.objects.filter(name=NAME).exists():
    sys.exit("!! part already exists")
cat = PartCategory.objects.filter(name__iexact="Electromechanical").first()
print(f"{NAME}\n  -> {loc.pathstring}, qty {QTY}, category {cat}")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

p = Part.objects.create(name=NAME, description=DESC, category=cat,
                        purchaseable=True, component=True, active=True)
s = StockItem.objects.create(part=p, location=loc, quantity=QTY,
                             notes=f"TALLIED {TODAY}: two in hand, each with a bracket. "
                                   "Untested — nothing has been spun up.")
Part.objects.filter(pk=p.pk).update(notes=NOTES, default_location=loc)
StockItem.objects.filter(pk=s.pk).update(stocktake_date=TODAY)
StockLocation.objects.filter(pk=loc.pk).update(description=BINDESC)

f = StockItem.objects.get(pk=s.pk)
assert float(f.quantity) == QTY and f.location_id == loc.pk, "row did not stick"
assert f.stocktake_date == TODAY, "stocktake did not stick"
assert Part.objects.get(pk=p.pk).default_location_id == loc.pk, "home did not stick"
print(f"\nOK  part #{p.pk}, stock #{f.pk} qty={float(f.quantity):g} in {loc.name}")

# cross-reference the controllers, since they are a natural pair with a caveat
c = Part.objects.get(pk=1138)
add = (f"\n\nNATURAL PAIR, WITH A CAVEAT: the 775 motors (#{p.pk}, B2-R5C1) are "
       "the obvious load for these. A 775 stalled pulls well past 10 A, and this "
       "board is fused at 10 A with no current limit and no soft-start, so a jam "
       "blows the fuse instead of backing off. Fine, and that is what the fuse is "
       "for — just do not read a blown fuse as a fault in the board.")
Part.objects.filter(pk=1138).update(notes=(c.notes or "") + add)
assert "NATURAL PAIR" in Part.objects.get(pk=1138).notes, "xref did not stick"
print("OK  cross-referenced #1138")

# and record what the cord retractor actually is, so it is not re-guessed
rb08 = StockLocation.objects.get(pk=481)
d = rb08.description or ""
if "SPRING-LOADED" not in d:
    nd = (d.rstrip() + " SPRING-LOADED, NOT MOTORISED — Scott 2026-08-28: the "
          "reels pull back voltage leads and are very lightweight, so the design "
          "uses springs. That is why the needle-roller THRUST bearings and "
          "compression springs exist and why no motor belongs to this project.")
    StockLocation.objects.filter(pk=481).update(description=nd[:600])
    assert "SPRING-LOADED" in StockLocation.objects.get(pk=481).description
    print("OK  RB-08 records that the cord retractor is spring-loaded")
