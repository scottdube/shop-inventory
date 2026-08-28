"""Catalogue the two reversing PWM DC motor speed controllers into B3-R5C4.

Identified 2026-08-28 from the board itself, since no model number is printed
anywhere on it and neither ALEDECO part already in the catalogue matches (both
of those are 1.8-12V 2A, a factor of five smaller and with no reverse).

What was read off the silicon, in order:
    LM324      quad op-amp -> the PWM is generated DISCRETELY, triangle
               oscillator plus comparator. No dedicated controller IC, so no
               current limit, no soft-start, no thermal fold-back.
    P75NF75    STP75NF75 N-ch MOSFET, 75V 80A, under the star heatsinks.
    L7812CV    ST 12V linear regulator, its own bent-fin heatsink. THIS is the
               voltage ceiling, not the FET.
    10A fuse   glass, in clips -> the design current.
    电机 motor / 电位器 potentiometer -> the only Chinese silkscreen; function
               labels, no rating.

    itq run scripts/add_pwm_controller.py            # dry run
    itq run scripts/add_pwm_controller.py --commit
"""
import argparse, datetime, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory                       # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

BIN, QTY = "B3-R5C4", 2
TODAY = datetime.date.today()
NAME = "PWM DC Motor Speed Controller, reversing, 10A (LM324 / STP75NF75)"
DESC = ("Reversing PWM DC motor speed controller. LM324 discrete PWM, STP75NF75 "
        "MOSFETs, L7812CV regulator, 10A fuse, panel pot and 3-position I-O-II "
        "rocker on flying leads. No model number anywhere on the board.")
NOTES = (
 "IDENTIFIED FROM THE SILICON, 2026-08-28. Nothing on this board carries a model "
 "number or a rating -- the only Chinese silkscreen is 电机 (motor) and 电位器 "
 "(potentiometer), which are function labels. Everything below was read off the "
 "parts themselves.\n\n"
 "SUPPLY CEILING IS 35 V, SET BY THE REGULATOR AND NOT THE FET. This is the trap "
 "on this board. The MOSFETs are STP75NF75 -- 75 V, 80 A -- so anyone reading the "
 "power devices concludes it will take 48 V happily. It will not: the L7812CV "
 "housekeeping regulator has an absolute maximum input of 35 V and sits directly "
 "across the supply. Feed this 48 V and the regulator dies first, probably taking "
 "the LM324 with it, while the FETs sit there unbothered.\n"
 "  Usable:   roughly 12-30 V DC\n"
 "  Never:    above 35 V, absolute\n"
 "Below about 15 V the 7812 drops out of regulation and gate drive softens; the "
 "board will likely still run at 12 V, just less hard. Untested.\n\n"
 "CURRENT: 10 A, set by the glass fuse. The FETs are rated far beyond that and "
 "the star heatsinks are small, so 10 A is a thermal figure, not a silicon one. "
 "Do not fit a larger fuse to get more current.\n\n"
 "STOP THE MOTOR BEFORE REVERSING. There is no H-bridge here -- the LM324 cannot "
 "drive one -- so the I-O-II rocker is mechanically swapping the motor leads. A "
 "spinning DC motor is a generator, and flipping its leads while it turns puts "
 "the supply and the back-EMF in series across the MOSFETs. The centre-off "
 "position exists for exactly this: pause in O, let it stop, then select. "
 "Snapping I straight to II is how these die, and a 10 A glass fuse is nowhere "
 "near fast enough to save a FET.\n\n"
 "NO CURRENT LIMIT AND NO SOFT-START. A discrete LM324 PWM has neither. A stalled "
 "motor draws locked-rotor current until the fuse decides otherwise.\n\n"
 "NOT the ALEDECO parts #29 / #428 already in this catalogue -- those are "
 "1.8-12 V 2 A with no reverse. Those two are also a duplicate pair of each "
 "other, both at zero stock, and are queued for merging.\n\n"
 "No purchase order or supplier part in this system matches this board; vendor "
 "and date unknown, so none is claimed.")
BINDESC = ("MOTOR SPEED CONTROLLERS — reversing PWM boards with their pots and "
           "I-O-II rockers on flying leads. A LARGE drawer by necessity: the "
           "board alone is small, but the panel pot and switch tails are not. "
           "Neighbours the BTS7960 drivers at B3-R6C1. "
           "[6 x 4-9/16 x 2-3/16 in, large]")
STOCKNOTE = (f"TALLIED {TODAY}: Scott confirmed two in hand. Untested — nothing "
             "has been powered up, so 'works' is not claimed. Read the part "
             "notes before connecting: the 35 V ceiling is set by the L7812CV "
             "regulator, not by the 75 V MOSFETs.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

locs = list(StockLocation.objects.filter(name__iexact=BIN))
if len(locs) != 1:
    sys.exit(f"!! {BIN} matched {len(locs)} locations")
loc = locs[0]
if StockItem.objects.filter(location=loc).exists():
    sys.exit(f"!! {BIN} is not empty — refusing to file blind")
cat = PartCategory.objects.filter(name__iexact="Power").first()
if Part.objects.filter(name=NAME).exists():
    sys.exit("!! part already exists")
print(f"{NAME}\n  -> {loc.pathstring}, qty {QTY}, category {cat}")
print(f"  bin was: {(loc.description or '')[:60]}")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

p = Part.objects.create(name=NAME, description=DESC, category=cat,
                        purchaseable=True, component=True, active=True)
s = StockItem.objects.create(part=p, location=loc, quantity=QTY, notes=STOCKNOTE)
Part.objects.filter(pk=p.pk).update(notes=NOTES, default_location=loc)
StockItem.objects.filter(pk=s.pk).update(stocktake_date=TODAY)
StockLocation.objects.filter(pk=loc.pk).update(description=BINDESC)

f = StockItem.objects.get(pk=s.pk)
assert float(f.quantity) == QTY and f.location_id == loc.pk, "row did not stick"
assert f.stocktake_date == TODAY, "stocktake did not stick"
assert Part.objects.get(pk=p.pk).default_location_id == loc.pk, "home did not stick"
assert "35 V" in Part.objects.get(pk=p.pk).notes, "notes did not stick"
assert StockLocation.objects.get(pk=loc.pk).description == BINDESC, "bin desc did not stick"
print(f"\nOK  part #{p.pk}, stock #{f.pk} qty={float(f.quantity):g} in {loc.name}")
