"""Merge #152 into #57, rename it, and file 10 into B3-R4C7.

Scott 2026-08-28: R4C7 works with a divider. Better than the A3 bin proposed
here — it keeps them in the sensor row, and pairing with the VL53L1X is coherent
since both are optical.

THE OLD HOME WAS A GUESS AND WAS WRONG. #57 carried "Placed in B3-R3C1 (ICs) --
INFERRED from the drawer label; verify." Scott: "I don't really see these as an
IC. I see these more as a module." Correct -- an IC is a chip you solder down;
this is a carrier board with an LM393, an indicator LED and a header. The guess
put it in the drawer you would open looking for a chip.

DUPLICATE PAIR, the third of this shape. #57 came from purchase history and
#152 from the listing text, same product, same 2024-01-07 order, both at zero
stock. #26/#153 (BTS7960) and #29/#428 (ALEDECO) are the same importer
behaviour. #153 was already merged into #26, so this follows that precedent.

RENAMED off the vendor. "EC Buying" is who sold it, not what it is, and it was
the first thing anyone would read. LM393 is the term somebody would search for.

    itq run scripts/file_speed_sensors.py            # dry run
    itq run scripts/file_speed_sensors.py --commit
"""
import argparse, datetime, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from company.models import Company, SupplierPart                 # noqa: E402
from part.models import Part                                     # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

KEEP, DUP, BIN, QTY = 57, 152, "B3-R4C7", 10
ASIN, TODAY = "X003YG8RRB", datetime.date.today()
NAME = "IR Slotted Optical Speed Sensor Module (LM393)"
DESC = ("Slotted optical interrupter on a carrier board -- IR emitter and "
        "phototransistor either side of a ~5 mm gap, LM393 comparator, indicator "
        "LED, digital output. Reads a slotted disc on a shaft for speed or "
        "position. 3-pin header (VCC/GND/OUT). Sold in 10-packs by EC Buying.")
NOTES = (
 f"TALLIED {TODAY}: Scott counted 10.\n\n"
 "A MODULE, NOT AN IC, and that distinction cost this part its home for two "
 "years. It was auto-placed in B3-R3C1 (ICs) by inference from a drawer label, "
 "flagged 'verify', and never verified. An IC is a chip you solder down; this is "
 "a populated carrier board. Now in B3-R4C7, the sensor row, sharing a divided "
 "drawer with the VL53L1X -- both optical sensing.\n\n"
 "HOW IT WORKS AND WHAT IT NEEDS: the beam is broken by a disc, so it counts "
 "edges, not revolutions. Pulses per turn equals slots per turn -- YOU supply "
 "the disc, and its slot count is what sets your resolution. Output is a clean "
 "digital square wave from the LM393, not an analogue level.\n\n"
 "NO DIRECTION SENSE. One channel means it cannot tell forward from reverse. "
 "Pairing it with the reversing PWM controllers (#1138) gives speed feedback "
 "only -- the controller knows which way it commanded, but the sensor cannot "
 "confirm it. Quadrature needs two channels offset by a quarter slot.\n\n"
 "PART OF THE 2024-01-07 ORDER, which was one project bought in one go: this "
 "sensor, the 775 motors (#1139), the BTS7960 H-bridge (#26), an MGN9 200 mm "
 "linear rail (#1117) and a CD74HC4067 multiplexer (#436). Motor, driver, "
 "feedback and rail -- a motorised linear slide with position feedback. Half of "
 "it was already on shelves in three separate bins with nothing recording that "
 "the pieces belonged together.\n\n"
 f"MERGED: part #{DUP} was the same product seeded from the listing text while "
 f"#{KEEP} came from purchase history. Third occurrence of that importer "
 "behaviour -- see #26/#153 (already merged) and #29/#428 (still open).")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

keep, dup = Part.objects.get(pk=KEEP), Part.objects.get(pk=DUP)
loc = StockLocation.objects.get(name__iexact=BIN)
print(f"keep  #{keep.pk} {keep.name[:52]}  stock={float(keep.total_stock):g}")
print(f"merge #{dup.pk} {dup.name[:52]}  stock={float(dup.total_stock):g}")
print(f"  -> rename to: {NAME}")
print(f"  -> {loc.pathstring}, qty {QTY}")
if StockItem.objects.filter(part=dup).exists():
    sys.exit("!! the duplicate has stock rows — needs a real transfer, not a deactivate")
if StockItem.objects.filter(part=keep).exists():
    sys.exit("!! keeper already has stock rows — refusing to double-file")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# 1. retire the duplicate. It has no stock, so deactivating is the whole merge.
Part.objects.filter(pk=DUP).update(
    active=False,
    notes=(dup.notes or "") + f"\n\nMERGED into part #{KEEP} on {TODAY} and "
          "deactivated. Same product, seeded twice by the importer: this record "
          "came from the listing text, #57 from purchase history. No stock was "
          "attached to this row, so nothing moved.")
assert not Part.objects.get(pk=DUP).active, "deactivate did not stick"
print(f"OK  #{DUP} deactivated")

# 2. rename, re-home, re-describe the keeper
Part.objects.filter(pk=KEEP).update(name=NAME, description=DESC, notes=NOTES,
                                    default_location=loc)
k = Part.objects.get(pk=KEEP)
assert k.name == NAME and k.default_location_id == loc.pk, "keeper did not stick"
print(f"OK  #{KEEP} renamed and homed to {loc.name}")

# 3. supplier part, so the ASIN is findable next time
amazon = Company.objects.get(name="Amazon", is_supplier=True)
if not SupplierPart.objects.filter(SKU=ASIN).exists():
    sp = SupplierPart.objects.create(part=k, supplier=amazon, SKU=ASIN,
                                     pack_quantity="10",
                                     link=f"https://www.amazon.com/dp/{ASIN}")
    assert SupplierPart.objects.get(pk=sp.pk).SKU == ASIN
    print(f"OK  SupplierPart {ASIN} under Amazon, pack=10")

# 4. the stock
s = StockItem.objects.create(part=k, location=loc, quantity=QTY,
                             notes=f"TALLIED {TODAY}: Scott counted 10 out of the "
                                   "EC Buying bag. Untested.")
StockItem.objects.filter(pk=s.pk).update(stocktake_date=TODAY)
f = StockItem.objects.get(pk=s.pk)
assert float(f.quantity) == QTY and f.stocktake_date == TODAY, "stock did not stick"
print(f"OK  stock #{f.pk} qty={float(f.quantity):g} in {loc.name}")

# 5. the drawer is now shared and divided — say so
d = loc.description or ""
nd = ("OPTICAL SENSING, DIVIDED DRAWER. VL53L1X time-of-flight distance sensor "
      "(Pololu carrier) on one side; IR slotted optical speed sensors on the "
      "other. Split by Scott 2026-08-28 -- the speed sensors had been "
      "auto-placed in B3-R3C1 (ICs) by inference and are modules, not ICs. "
      "[6 x 2-7/32 x 1-9/16 in, small]")
StockLocation.objects.filter(pk=loc.pk).update(description=nd)
assert "DIVIDED DRAWER" in StockLocation.objects.get(pk=loc.pk).description
print("OK  B3-R4C7 described as a divided drawer")
