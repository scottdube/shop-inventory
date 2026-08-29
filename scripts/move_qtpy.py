"""Move the QT Py boards B3-R3C4 -> B3-R3C5. Physical room, not a re-think.

Scott 2026-08-29: "Move them next door to r three c five. There's just not
enough room in the other bin yet anymore."

C5 is a good landing anyway: it is the Adafruit STEMMA QT bin, and the QT Py
carries a STEMMA QT connector — the boards and the sensors they drive now share
a drawer.

BUT THE FOOTPRINT FACT MUST NOT BE LOST WITH THE MOVE. C4 was renamed this
morning to "XIAO / QT PY FORM FACTOR" because the two are pin-compatible at
21 x 17.5 mm. With the QT Pys gone that name is a false claim about C4's
contents, so it reverts — and BOTH bins now carry the cross-reference, because
the reason to know they are interchangeable does not go away just because they
sit in different drawers. A fact that survives only in the bin it was written
in is a fact you lose the next time something moves.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part                                     # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

PART, STOCK, SRC, DST = 1148, 737, "B3-R3C4", "B3-R3C5"

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

src = StockLocation.objects.get(name__iexact=SRC)
dst = StockLocation.objects.get(name__iexact=DST)
s = StockItem.objects.get(pk=STOCK)
print(f"stock #{s.pk} {s.part.name[:48]}  {src.name} -> {dst.name}")
print(f"  {dst.name} holds:")
for x in StockItem.objects.filter(location=dst):
    print(f"    [{x.pk}] {float(x.quantity):g}x {x.part.name[:52]}")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

StockItem.objects.filter(pk=STOCK).update(location=dst)
Part.objects.filter(pk=PART).update(default_location=dst)
assert StockItem.objects.get(pk=STOCK).location_id == dst.pk, "move did not stick"
assert Part.objects.get(pk=PART).default_location_id == dst.pk, "home did not stick"
print(f"OK  moved to {dst.pathstring}")

C4 = ("XIAO dev boards — Seeed XIAO ESP32-S3, plus 2.4GHz FPC antennas that fit "
      "the S3 and C6. Was briefly renamed to the FORM FACTOR when the QT Py "
      "RP2040 boards landed here; they moved to B3-R3C5 on 2026-08-29 for room, "
      "so this name reverts. THE FOOTPRINT FACT STILL HOLDS: XIAO and Adafruit "
      "QT Py share 21 x 17.5 mm castellated outlines and pin order, so they are "
      "interchangeable in a socket — the QT Pys are simply one drawer over. "
      "SAME SIZE IS NOT SAME CAPABILITY: RP2040 has no radio at all. "
      "[6 x 2-7/32 x 1-9/16 in, small]")
C5 = ("ADAFRUIT STEMMA QT — the boards and the sensors they drive. TLV493D "
      "3-axis magnetometers, JST SH 4-pin cables, and the QT Py RP2040 dev "
      "boards (moved from B3-R3C4 on 2026-08-29 for room; they carry a STEMMA QT "
      "connector, so this is a coherent home rather than an overflow). "
      "The QT Py shares its 21 x 17.5 mm footprint and pinout with the Seeed "
      "XIAO boards next door in B3-R3C4 — interchangeable mechanically, NOT "
      "electrically: RP2040 has no WiFi, no Bluetooth, no radio. "
      "[6 x 2-7/32 x 1-9/16 in, small]")
StockLocation.objects.filter(pk=src.pk).update(description=C4)
StockLocation.objects.filter(pk=dst.pk).update(description=C5)
assert "FORM FACTOR" not in StockLocation.objects.get(pk=src.pk).description \
    or "Was briefly renamed" in StockLocation.objects.get(pk=src.pk).description
assert "QT Py RP2040 dev" in StockLocation.objects.get(pk=dst.pk).description
print("OK  both bin descriptions updated; the footprint cross-reference is on both")

n = Part.objects.get(pk=PART).notes.replace(
 "SAME FOOTPRINT AND PINOUT AS THE SEEED XIAO boards in this bin.",
 "SAME FOOTPRINT AND PINOUT AS THE SEEED XIAO boards in B3-R3C4, next door.")
Part.objects.filter(pk=PART).update(notes=n)
assert "next door" in Part.objects.get(pk=PART).notes, "part note did not stick"
print("OK  part note corrected — the XIAOs are no longer 'in this bin'")
