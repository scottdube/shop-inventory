#!/usr/bin/env python3
"""Dissolve the Glarks terminal block kit (#283) into its real components.

Wire-shelf stock-in, 2026-09-16. Scott produced the kit; #283 was already
catalogued from purchase history (ASIN B07Y21W11W, 2022-08-12, $17.98) with
ZERO stock rows. The listing decomposes it exactly:

    8 pcs   barrier terminal strips, 3/4/5/6/7/8/10/12 position, 600V 15A
    16 pcs  pre-insulated barrier strips (jumper bars)
    100 pcs insulated fork wire connectors
    ---
    124 pcs

SPLIT BY POSITION COUNT, on Scott's answer. The question anyone actually asks
of these is "have I got a 10-position?", and a single kit row cannot answer it
without walking to the drawer. The fuse kit #1143 is still one row and its own
notes call that a deferral rather than a decision; this one gets the decision.

COUNTS ARE TWO DIFFERENT TIERS AND ARE MARKED AS SUCH:
  * the blocks are TALLIED -- Scott: "The only one missing is the three. The
    rest of them are there." That is a count of a set small enough to see at a
    glance, so no [ESTIMATE] marker.
  * the forks and jumper bars are CARD FIGURES -- Scott: "card figure". The
    kit has demonstrably been drawn on (the 3-position is gone), so 100 and 16
    are upper bounds, not counts. They carry [ESTIMATE] at the START of the
    notes, where notes__startswith can find them.

#283 IS KEPT AT ZERO STOCK, NOT DELETED. Same treatment as the retired
SparkFun kit: the purchase history, the ASIN and every note naming it still
resolve, and the kit row stops competing with the component rows for the same
physical objects.

    itq run scripts/dissolve_glarks_kit.py
    itq run scripts/dissolve_glarks_kit.py --commit
"""
import os
import sys
from decimal import Decimal

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
CAT = PartCategory.objects.get(pk=18)            # flat Connectors, 54 parts
LOC = StockLocation.objects.get(pk=568)          # B0-R2C3
KIT = 283

BLOCK_NOTE = """Barrier-style terminal block: two rows of screw terminals bridged in pairs, under a clear insulating cover, with a numbered legend. Body marked WEIDU TB-15xx, rated **600 V 15 A**.

**NOT interchangeable with the PCB terminal blocks in A3-R8C6/C7.** Those are 2.54 mm and 5.08 mm blocks that SOLDER INTO A BOARD. These are chassis-mount barrier strips that take ring or fork terminals under a screw, and they are a different class of thing entirely despite the shared words "terminal block".

**THE PAIRS ARE BRIDGED, which is the whole point and the usual surprise.** Each numbered position connects the front screw to the back screw. It is a junction, not a switch — wire in one side and out the other.

From the Glarks 124-piece kit, #283, ASIN B07Y21W11W, bought 2022-08-12. The kit is dissolved into per-position parts so "have I got a 10-position?" is answerable from the record."""

BLOCKS = [4, 5, 6, 7, 8, 10, 12]     # the 3-position is gone; Scott, 2026-09-16

EXTRAS = [
    dict(
        name="Fork Terminal, insulated crimp, on carrier strip (Glarks kit)",
        qty=Decimal("100"),
        desc=("Insulated fork / spade crimp wire terminal, supplied on a red "
              "plastic carrier strip. From the Glarks 124-piece terminal "
              "block kit."),
        kw="fork terminal, spade terminal, crimp terminal, wire connector, carrier strip, glarks",
        notes=("[ESTIMATE] 100 is the CARD FIGURE from the kit listing, not a count. "
               "Scott, 2026-09-16: \"card figure\". The kit has demonstrably been "
               "drawn on -- the 3-position block is gone -- so 100 is an UPPER "
               "BOUND and the real number is very likely lower. Count them when "
               "one is actually needed in quantity.\n\n"
               "SUPPLIED ON A CARRIER STRIP, which is how they arrived and how "
               "they are stored. Break one off as needed.\n\n"
               "WIRE GAUGE AND STUD SIZE ARE UNRECORDED. The listing says only "
               "\"insulated fork wire connector\" and neither the kit nor the "
               "carrier states a range. Measure before specifying one into a "
               "build.\n\n"
               "From the Glarks kit #283, ASIN B07Y21W11W, bought 2022-08-12."),
    ),
    dict(
        name="Barrier Strip Jumper, pre-insulated (Glarks kit)",
        qty=Decimal("16"),
        desc=("Pre-insulated jumper bar for bridging adjacent positions on a "
              "barrier terminal block. From the Glarks 124-piece kit."),
        kw="jumper bar, barrier strip jumper, shorting bar, terminal block jumper, glarks",
        notes=("[ESTIMATE] 16 is the CARD FIGURE from the kit listing, not a count. "
               "Scott, 2026-09-16: \"card figure\". Upper bound -- the kit has been "
               "used.\n\n"
               "WHAT THESE ARE FOR: bridging adjacent positions on a barrier block "
               "so several terminals share one feed, which is how you turn a strip "
               "into a distribution bus. Without them each pair stands alone.\n\n"
               "From the Glarks kit #283, ASIN B07Y21W11W, bought 2022-08-12."),
    ),
]

print(f"destination: {LOC.pathstring}")
made = []

for n in BLOCKS:
    name = f"Barrier Terminal Block, {n}-position, 600V 15A, dual row (WEIDU TB-15{n:02d})"
    p = Part.objects.filter(name=name).first()
    print(f"  {'exists' if p else 'create'}  {name[:62]}  qty 1")
    if not COMMIT:
        continue
    if not p:
        p = Part.objects.create(
            name=name,
            description=(f"Chassis-mount barrier terminal block, {n} positions, "
                         f"dual row screw, 600 V 15 A, clear cover, numbered "
                         f"legend. Body marked WEIDU."),
            category=CAT, default_location=LOC,
            keywords=(f"barrier terminal block, terminal strip, {n} position, "
                      f"600V 15A, dual row, screw terminal, WEIDU, chassis mount"),
            notes=BLOCK_NOTE, active=True, purchaseable=False, component=True)
    if not StockItem.objects.filter(part=p).exists():
        StockItem.objects.create(
            part=p, location=LOC, quantity=Decimal("1"),
            notes=("COUNTED by Scott 2026-09-16: \"The only one missing is the "
                   "three. The rest of them are there.\" Seven of the kit's eight "
                   "blocks present, one each. Tallied, not an estimate."))
    made.append(p)

for e in EXTRAS:
    p = Part.objects.filter(name=e["name"]).first()
    print(f"  {'exists' if p else 'create'}  {e['name'][:62]}  qty {float(e['qty']):g} [ESTIMATE]")
    if not COMMIT:
        continue
    if not p:
        p = Part.objects.create(
            name=e["name"], description=e["desc"], category=CAT,
            default_location=LOC, keywords=e["kw"], notes=e["notes"],
            active=True, purchaseable=False, component=True)
    if not StockItem.objects.filter(part=p).exists():
        StockItem.objects.create(part=p, location=LOC, quantity=e["qty"],
                                 notes=e["notes"])
    made.append(p)

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

kit = Part.objects.get(pk=KIT)
add = ("\n\n## DISSOLVED 2026-09-16 — kept at zero stock, not deleted\n\n"
       "This kit was opened and split into per-component parts, all filed to "
       "B0-R2C3:\n\n"
       + "\n".join(f"- #{p.pk} {p.name}" for p in made) +
       "\n\nThe kit record stays so the purchase history, the ASIN and any note "
       "naming it still resolve — the same treatment as the retired SparkFun "
       "kit. ZERO STOCK HERE MEANS DISSOLVED, NOT MISSING: the objects exist, "
       "they are just counted under the component parts now. Do not add stock "
       "back to this row; it would double-count them.\n\n"
       "The 3-position block was already gone when the kit was catalogued "
       "(Scott, 2026-09-16), so only seven of the eight blocks exist.")
if "DISSOLVED 2026-09-16" not in (kit.notes or ""):
    Part.objects.filter(pk=KIT).update(notes=(kit.notes or "") + add)
kit.refresh_from_db()

print(f"\ncreated/confirmed {len(made)} parts")
print(f"kit #{KIT} marked dissolved: {'DISSOLVED 2026-09-16' in kit.notes}")
print(f"kit stock rows (must be 0): {StockItem.objects.filter(part_id=KIT).count()}")
print(f"B0-R2C3 now holds {StockItem.objects.filter(location=LOC).count()} rows")
