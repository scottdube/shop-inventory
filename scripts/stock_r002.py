"""Stock the R002 shunt salvaged off the INA228 breakout, and home it in B3-R3C2.

The module (part 1164, stock #765) shipped with a 2 mOhm chip shunt across
VIN+/VIN-. It was desoldered on 2026-09-02 so the INA228 could drive the
external 100 A shunt instead; VIN+ to VIN- then read 35 MOhm, confirming open.

MY RECOMMENDATION WAS NOT TO STOCK IT and Scott overruled that, so this exists.
The argument against is still worth having on the record because it is what the
notes have to defend against: a 2 mOhm chip reads as a dead short on every meter
in this shop, so its tolerance cannot be re-verified after a rework, and a
sense resistor whose tolerance is unknown is a resistor whose whole point is
unknown. The shrink-fit BOM's plan was to keep it taped to the module as return
insurance; the module is now staying (the 19.5 mm coil collapses the bus, so
CAN telemetry alone will not carry CR-01's dose), which removed that reason.

So the notes below carry the caveat instead of the record being refused: it is
stocked, and it says out loud what nobody can measure about it.

B3-R3C2 is Scott's pick. It is the SMD drawer and a small one — it holds the
8-value bridge rectifier kit and eight bagged values — so a single bagged chip
fits and sits with like company.

    itq run scripts/stock_r002.py             # dry run
    itq run scripts/stock_r002.py --commit
"""
import argparse
import datetime
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth import get_user_model      # noqa: E402
from part.models import Part                        # noqa: E402
from stock.models import StockItem, StockLocation   # noqa: E402

TODAY = datetime.date.today()
DRAWER, CAT, INA_PART, INA_STOCK = 311, 69, 1164, 765

NAME = "Current-Sense Resistor 2 mOhm, SMD (R002), salvaged from INA228 module"

DESC = ("Two-milliohm SMD current-sense resistor, marking R002, desoldered from "
        "the GODIYMODULES INA228 breakout so the chip could be driven from an "
        "external shunt instead. Package, power rating and tolerance all "
        "UNVERIFIED.")

NOTES = (
    "SALVAGED 2026-09-02 from the INA228 breakout (part %d, stock #%d, "
    "PO-0152). It was the module's onboard shunt across VIN+/VIN-; removing it "
    "is what lets the INA228 measure the shrink-fit rig's external 100 A shunt "
    "instead. After removal VIN+ to VIN- measured 35 MOhm, which against a "
    "~750 uOhm external shunt diverts about two parts in a hundred billion.\n\n"
    "WHAT IS NOT KNOWN ABOUT IT, and cannot be found out here:\n"
    "- TOLERANCE. 2 mOhm reads as a dead short on every meter in this shop, so "
    "no instrument here can re-verify it. Desoldering is also the stress that "
    "cracks a low-value chip's terminations, and a cracked one still looks "
    "perfect. DO NOT USE IT AS A CALIBRATION REFERENCE.\n"
    "- PACKAGE and POWER RATING. Never recorded, and the only marking is R002. "
    "Measure the body before designing it into anything.\n\n"
    "WHAT IT IS ACTUALLY GOOD FOR: putting the INA228 module back to stock "
    "form if it is ever repurposed as a standalone breakout on another project. "
    "That is the use this was kept for.\n\n"
    "Stocked at Scott's direction on %s. The recommendation had been to leave "
    "it taped to the module and give it no record, on the grounds that one "
    "sub-dollar unverifiable part in the catalogue is a false positive waiting "
    "for the next person searching for a current-sense resistor. That risk is "
    "real and this note is the mitigation — anyone who finds this row reads the "
    "UNVERIFIED block above before reaching for it.\n\n"
    "SUPERSEDES the shrink-fit BOM's on-arrival instruction to keep the R002 "
    "bagged and taped to the board. That instruction existed so the module "
    "could be returned within the 30-day window if the flat-draw test retired "
    "energy dosing. The module is staying: at 0.66 coupling the 19.5 mm coil "
    "collapses the bus 52 V to 18 V, which is exactly the non-flat load that "
    "CAN telemetry alone cannot integrate."
) % (INA_PART, INA_STOCK, TODAY)

STOCK_NOTES = (
    "ONE piece, and the count needs no ceremony: one resistor came off one "
    "board, and Scott has it in hand. Bagged and filed to B3-R3C2 on %s in the "
    "same act as printing its label.\n\n"
    "Its parent module (stock #%d) is on the assembly table with the shrink-fit "
    "rig and is NOT stock-form any more — it cannot measure current without an "
    "external shunt until this part goes back on it.\n\n"
    "Tolerance, package and power rating are all unverified. Read the part "
    "notes before using it for anything that depends on the value." % (TODAY, INA_STOCK)
)

DRAWER_DESC = (
    "SMD components — 8-value bridge rectifier kit (vendor no. 48-13), plus the "
    "2 mOhm R002 current-sense resistor salvaged off the INA228 breakout "
    "2026-09-02 (bagged, tolerance unverified). SMALL drawer: it takes the kit "
    "bag and not much else. The bulk LCSC cut-tape does NOT fit here. "
    "[6 x 2-7/32 x 1-9/16 in, small]"
)

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
drawer = StockLocation.objects.get(pk=DRAWER)

# Part.name caps at 100 and Part.description at 250 — budget before writing,
# not after truncation has eaten the discriminator.
print(f"name        {len(NAME):3d}/100  {NAME}")
print(f"description {len(DESC):3d}/250")
print(f"drawer desc {len(DRAWER_DESC):3d}       {drawer.pathstring}")
assert len(NAME) <= 100, "part name too long"
assert len(DESC) <= 250, "description too long"

# Check for a duplicate before creating — two importers have already entered the
# same item twice under different names.
dupes = Part.objects.filter(name__icontains="current-sense") | \
        Part.objects.filter(name__icontains="R002") | \
        Part.objects.filter(name__icontains="shunt")
dupes = dupes.distinct()
print(f"\nduplicate check: {dupes.count()} candidate(s)")
for d in dupes:
    print(f"  [{d.pk}] {d.name}")

existing = Part.objects.filter(name=NAME).first()
print(f"\npart: {'EXISTS ' + str(existing.pk) if existing else 'to create'} "
      f"in category {CAT}, home {drawer.name}")

if not a.commit:
    sys.exit("\nDRY RUN — add --commit")

p = existing or Part.objects.create(
    name=NAME, description=DESC, category_id=CAT, default_location=drawer,
    purchaseable=False, active=True)
Part.objects.filter(pk=p.pk).update(
    description=DESC, notes=NOTES, default_location=drawer, category_id=CAT)

si = StockItem.objects.filter(part=p, location=drawer).first()
if not si:
    si = StockItem.objects.create(part=p, location=drawer, quantity=1)
StockItem.objects.filter(pk=si.pk).update(
    notes=STOCK_NOTES, stocktake_date=TODAY, stocktake_user=user,
    delete_on_deplete=False)

StockLocation.objects.filter(pk=DRAWER).update(description=DRAWER_DESC)

# Point the module's row back at the resistor, now that it has a pk.
ina = StockItem.objects.get(pk=INA_STOCK)
StockItem.objects.filter(pk=INA_STOCK).update(
    notes=(ina.notes or "").rstrip() +
    f"\n\nThe removed R002 is stocked as part {p.pk}, stock #{si.pk}, "
    f"in B3-R3C2. Refitting it is what would return this module to stock form.")

# ---- verify ---------------------------------------------------------------
p.refresh_from_db()
si.refresh_from_db()
drawer.refresh_from_db()
ina.refresh_from_db()
fail = []
if p.default_location_id != DRAWER:
    fail.append("default_location did not stick")
if "UNVERIFIED" not in (p.notes or ""):
    fail.append("part notes did not stick")
if float(si.quantity) != 1:
    fail.append(f"quantity is {si.quantity}")
if si.location_id != DRAWER:
    fail.append("stock location did not stick")
if si.stocktake_date != TODAY:
    fail.append("stocktake_date did not stick")
if si.delete_on_deplete:
    fail.append("delete_on_deplete still True — a zero would erase these notes")
if "R002" not in (drawer.description or ""):
    fail.append("drawer description did not stick")
if f"stock #{si.pk}" not in (ina.notes or ""):
    fail.append("back-pointer on the INA228 row did not stick")

print(f"\npart [{p.pk}] {p.name}")
print(f"  category        {p.category.pathstring}")
print(f"  default_location {p.default_location.pathstring}")
print(f"stock [{si.pk}] qty={float(si.quantity):g} @ {si.location.pathstring} "
      f"counted {si.stocktake_date}")
print(f"drawer [{drawer.pk}] {drawer.description[:100]}...")
print(f"\n{'SUCCESS' if not fail else 'FAILED: ' + '; '.join(fail)}")
sys.exit(1 if fail else 0)
