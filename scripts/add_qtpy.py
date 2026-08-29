"""Adafruit QT Py RP2040 x2 into B3-R3C4, and broaden that bin to the FORM FACTOR.

The bin was "XIAO ESP32-S3 boards + 2.4GHz FPC antennas". QT Py and Seeed XIAO
share a footprint and pinout -- 21 x 17.5 mm, castellated, same pin order -- so
they are physically interchangeable in a socket or a carrier. Storing them apart
would hide that; storing them together means one drawer answers "what do I have
for this footprint".

Renaming rather than just adding, because a bin named for its first occupant is
how the second lands elsewhere. B3-R5C1 made that mistake calling itself 'ROUND
DISPLAYS' this morning and needed renaming three hours later.

NOT with the ESP32 boards (B3-R6C3): different silicon and, more to the point,
different size. NOT with the Adafruit STEMMA QT peripherals (B3-R3C5): that bin
is sensors and cables, and this is the thing you plug them into.
"""
import argparse, datetime, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory                       # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

BIN, QTY, TODAY = "B3-R3C4", 2, datetime.date.today()
NAME = "Adafruit QT Py RP2040 (PID 4900)"
DESC = ("Adafruit QT Py RP2040, product 4900. RP2040 dual-core Cortex-M0+, 8 MB "
        "QSPI flash, USB-C, STEMMA QT / Qwiic connector, NeoPixel, castellated "
        "edge pads. XIAO form factor, 21 x 17.5 mm. Supplied with a header strip.")
NOTES = (
 f"COUNTED {TODAY}: two — one bag opened with its header strip alongside, one "
 "still sealed.\n\n"
 "SAME FOOTPRINT AND PINOUT AS THE SEEED XIAO boards in this bin. 21 x 17.5 mm, "
 "castellated edges, same pin order — they drop into each other's sockets and "
 "carriers. That is why they share a drawer: the question you arrive with is "
 "\"what have I got for this footprint\", and one bin answers it.\n\n"
 "THEY ARE NOT SOFTWARE-COMPATIBLE, and the shared footprint is what makes that "
 "trap possible. RP2040 is not an ESP32: no WiFi, no Bluetooth, no radio of any "
 "kind. A design that swaps a XIAO ESP32 for a QT Py because it physically fits "
 "loses every wireless feature and gains nothing back. Check the requirement, "
 "not the outline.\n\n"
 "STEMMA QT / QWIIC ON BOARD, so it talks I2C to the TLV493D magnetometers and "
 "the JST SH cables in B3-R3C5 with no soldering. That pairing is the reason to "
 "reach for this board over a bare Pico.\n\n"
 "HEADERS ARE SUPPLIED LOOSE, NOT FITTED. Usable on a breadboard only after "
 "soldering, or use the castellations to surface-mount it onto a carrier.\n\n"
 "Adafruit PID 4900, W19597-E. No purchase order in this system matches it.")
BINDESC = ("XIAO / QT PY FORM FACTOR — 21 x 17.5 mm castellated dev boards, which "
           "are pin-compatible with each other whatever silicon is on them. "
           "Currently Seeed XIAO ESP32-S3 and Adafruit QT Py RP2040, plus 2.4GHz "
           "FPC antennas that fit the S3 and C6. Renamed from 'XIAO ESP32-S3 "
           "boards' 2026-08-29: the bin is about the FOOTPRINT, not one vendor. "
           "WARNING: same size does not mean same capability — the RP2040 boards "
           "have no radio at all. [6 x 2-7/32 x 1-9/16 in, small]")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.get(name__iexact=BIN)
if Part.objects.filter(name=NAME).exists():
    sys.exit("!! already exists")
cat = PartCategory.objects.filter(name__icontains="module").first() \
      or Part.objects.get(pk=503).category
print(f"{NAME}\n  -> {loc.pathstring}, qty {QTY}, category {cat}")
print(f"  bin was: {(loc.description or '')[:70]}")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

p = Part.objects.create(name=NAME, description=DESC, category=cat,
                        purchaseable=True, component=True, active=True)
s = StockItem.objects.create(part=p, location=loc, quantity=QTY,
                             notes=f"COUNTED {TODAY}: 2 — one opened with header, "
                                   "one sealed.")
Part.objects.filter(pk=p.pk).update(notes=NOTES, default_location=loc)
StockItem.objects.filter(pk=s.pk).update(stocktake_date=TODAY)
StockLocation.objects.filter(pk=loc.pk).update(description=BINDESC)
f = StockItem.objects.get(pk=s.pk)
assert float(f.quantity) == QTY and f.stocktake_date == TODAY, "stock did not stick"
assert Part.objects.get(pk=p.pk).default_location_id == loc.pk, "home did not stick"
assert "FORM FACTOR" in StockLocation.objects.get(pk=loc.pk).description
print(f"\nOK  part #{p.pk}, stock #{f.pk} qty=2 in {loc.name}; bin renamed")
