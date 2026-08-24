"""Stock the TCRT5000 modules (#718) and give them a home of their own.

NOT a create. Part #718 already existed, and the duplicate guard in the first
version of this script refused before writing anything -- the check earning its
keep, since a second "IR Reflective Sensor Module" under a slightly different
name is exactly the accretion two importers have already caused here.

**This closes a question the record was holding open.** #718's note says
"10 bought ... On-hand quantity is NOT known -- a photo showed two bags, which
is not the same as two remaining. Count at the next bin check." Scott counted 9
on 2026-08-24 while filing them. Bought 10, nine left, one used.

**And it corrects a home.** #718 pointed at B3-R4C6, which is the REMOTE-CONTROL
IR drawer -- VS1838B receiver, HA blaster/learner, emitter cables. A reflective
line sensor and a 38 kHz remote receiver share the word "IR" and nothing else;
filing them together means every future search for one wades through the other.

Nine identical modules get their OWN drawer rather than joining the mixed
"small modules" drawer A3-R2C4. Nine of one thing in a grab-bag is nine things
to fish past every time somebody wants something else, and it is much harder to
cycle-count than a drawer whose whole contents are one line.

Identification, kept honest about what was actually read:

  VERIFIED from the boards -- 4-pin header silkscreened VCC / GND / DO / AO;
  reflective emitter/detector pair in one black block (dark IR LED beside a
  blue phototransistor); 8-pin SOIC comparator; blue threshold trimpot; two
  indicator LEDs marked 电源指示 (power) and 开关指示 (output); 102 and 103
  SMD resistors.

  INFERRED -- that the sensor is a TCRT5000 and the comparator an LM393. Both
  are the overwhelmingly common parts in this exact board, but neither package
  marking was read. The name says "TCRT5000-type" for that reason.

The bag label "29114 / 2G01-01-03-06 / 80207-2213" is a warehouse lot code, not
an MPN, so it is recorded as provenance and NOT as a part number.

    itq run scripts/add_ir_reflective.py
    itq run scripts/add_ir_reflective.py --commit
"""
import argparse
import datetime
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.db.models import Q                     # noqa: E402
from part.models import Part, PartCategory         # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

PART_PK = 718
DESC = ("TCRT5000 reflective optical sensor with LM393 comparator, ~1-25mm "
        "range. Digital + analog out, trimpot threshold. Tells dark from light "
        "a few mm away — line following, encoder wheels, index/home sensing. "
        "NOT a distance sensor; that is the VL53L1X.")
QTY = 9
DRAWER = "A3-R1C3"
DRAWER_DESC = ("IR REFLECTIVE / LINE SENSORS. TCRT5000-type modules, 4-pin "
               "VCC/GND/DO/AO with LM393 comparator and threshold trimpot. "
               "Reach for one when you need to know 'is something there' or "
               "'is this stripe dark' a few millimetres away — counting slots "
               "on a wheel, finding a home position, following a line. NOT for "
               "measuring distance; the VL53L1X in B3-R4C7 is that. Kept "
               "separate from the remote-control IR in B3-R4C6, which shares "
               "the word and nothing else. Established 2026-08-24; drawer was "
               "VERIFIED EMPTY 2026-08-23. [6 x 2-7/32 x 1-9/16 in, small]")
NOTES = """## What it is

Reflective optical sensor: an IR emitter and a phototransistor facing the SAME
direction, so it reads light bounced back off a surface in front of it.

- **DO** — digital, high/low against the trimpot threshold, via the comparator
- **AO** — the raw analogue reading, which is what you want if you are
  thresholding in software or looking at gradients

## When you reach for it

- following a line, or finding the edge of one
- **encoder wheels** — counting stripes or slots to measure rotation
- index / home detection on a moving axis
- "is the tape/paper/part still there"

## Traps

- **It is a REFLECTANCE sensor, not a distance sensor.** Useful range is a few
  millimetres — best around 2-3 mm, falling off badly past ~15 mm. If the
  question is *how far away*, the VL53L1X in B3-R4C7 is the right part.
- **Ambient IR swamps it.** Sunlight or a bright shop lamp can hold it
  triggered. Shroud it, or read AO and subtract a baseline.
- **Surface colour matters more than distance.** Matte black vs white is what
  it really distinguishes; shiny black can read as bright.

## Identification

Verified from the boards: VCC/GND/DO/AO silkscreen, reflective pair in one
black block, 8-pin SOIC comparator, blue trimpot, LEDs marked 电源指示 (power)
and 开关指示 (output), 102/103 SMD resistors.

INFERRED, not read: that the sensor is a TCRT5000 and the comparator an LM393.
Neither package marking was read, which is why the name says "TCRT5000-type".
Read the markings under magnification to settle it.

## Provenance

Antistatic bag label: `29114 / 2G01-01-03-06 / 80207-2213`. A warehouse lot
code, not a manufacturer part number — recorded here rather than in IPN so
nobody tries to reorder by it.
"""

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

assert len(DESC) <= 250, f"description is {len(DESC)} chars"

part = Part.objects.get(pk=PART_PK)
locs = list(StockLocation.objects.filter(name__iexact=DRAWER))
assert len(locs) == 1, f"{DRAWER} matched {len(locs)}"
loc = locs[0]

print(f"#{part.pk} {part.name}")
print(f"   home  {part.default_location}  ->  {loc.pathstring}")
print(f"   stock rows now: {part.stock_items.count()}")
print(f"   drawer {DRAWER} holds {loc.stock_items.count()} item(s)")

if part.stock_items.exists():
    print("!! already has stock — refusing to double-count")
    raise SystemExit(1)
if loc.stock_items.exists():
    print(f"!! {DRAWER} is not empty — pick another drawer")
    raise SystemExit(1)

print(f"\n   stock {QTY} @ {DRAWER}, hand-counted by Scott 2026-08-24")
print(f"   (purchase history says 10 bought 2018-04-09 — so one has been used)")

if not a.commit:
    print("\nDRY RUN — add --commit")
    raise SystemExit

StockLocation.objects.filter(pk=loc.pk).update(description=DRAWER_DESC)
assert StockLocation.objects.get(pk=loc.pk).description == DRAWER_DESC
print(f"\nOK  {DRAWER} described")

Part.objects.filter(pk=PART_PK).update(
    default_location=loc, description=DESC,
    keywords=("tcrt5000, tcrt, ir reflective, reflective sensor, line tracking, "
              "line following, line sensor, opto reflective, encoder wheel, "
              "index sensor, lm393, DO AO, obstacle"))
f = Part.objects.get(pk=PART_PK)
assert f.default_location_id == loc.pk and f.keywords, "part update did not stick"
print(f"OK  #{PART_PK} home -> {f.default_location.pathstring}, keywords set")

si = StockItem.objects.create(
    part=f, location=loc, quantity=QTY,
    stocktake_date=datetime.date(2026, 8, 24),
    notes=("Hand-counted 9 on 2026-08-24 by Scott while filing them into "
           "A3-R1C3 — a put-away done by a person who confirms the contents is "
           "a count. This ANSWERS the open question on the part record: 10 were "
           "bought 2018-04-09 and the on-hand figure was explicitly unknown, so "
           "one has been used. Bag lot code 29114 / 2G01-01-03-06 / 80207-2213 "
           "— a warehouse code, not an MPN."))
chk = StockItem.objects.get(pk=si.pk)
assert float(chk.quantity) == QTY and chk.location_id == loc.pk
assert str(chk.stocktake_date) == "2026-08-24"
print(f"OK  stock #{chk.pk} qty={float(chk.quantity):g} @ {chk.location.name} "
      f"stocktake={chk.stocktake_date}")
