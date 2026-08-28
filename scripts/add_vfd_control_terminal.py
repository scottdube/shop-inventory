"""The VFD control terminal block: 18-way, 3.5mm, PCB-mount. Into A3-R8C7.

Scott 2026-08-28: "This slot is directly to the PC board." One piece, solder
tails on both rows, unsoldered from the dead VFD's control board. Not a plug and
socket pair -- reusing it means soldering it to a board.

Filed with the 5.08mm PCB terminal blocks rather than given its own bin. The
A3-R8 neighbourhood is organised by pitch (C6 = 2.54mm, C7 = 5.08mm) and 3.5mm
has no bin, but ONE salvaged connector does not earn a drawer on a wall that is
89% full. C7 becomes "5.08mm plus odd-pitch oddments", which needs no divider
and keeps terminal blocks findable in one place.

The pinout is the valuable part and is recorded in full: it is the only surviving
record of what that drive's control interface could do.

    itq run scripts/add_vfd_control_terminal.py            # dry run
    itq run scripts/add_vfd_control_terminal.py --commit
"""
import argparse, datetime, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory                       # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

BIN, QTY, TODAY = "A3-R8C7", 1, datetime.date.today()
NAME = "Terminal Block, PCB-mount 3.5mm, 18-position (2x9), VFD control"
DESC = ("18-position PCB-mount terminal block, two rows of nine, 3.5 mm pitch, "
        "grey. Wire entry on the front face, solder tails underneath. Salvaged "
        "from the control board of the dead VFD.")
NOTES = (
 f"TALLIED {TODAY}: one, salvaged from the dead VFD's control board.\n\n"
 "PCB-MOUNT, NOT A PLUG AND SOCKET. Both rows are solder tails. Reusing it means "
 "soldering it to a board — it is not something you mate a cable end into. That "
 "was checked rather than assumed.\n\n"
 "PITCH IS 3.5 mm, measured by Scott. It therefore matches neither neighbour: "
 "A3-R8C6 is 2.54 mm and this bin is 5.08 mm. Filed here anyway because one "
 "salvaged connector does not earn its own drawer on a wall that is 89% full — "
 "but it will NOT mate with anything else in this bin.\n\n"
 "SILKSCREEN, read off the block 2026-08-28 — this is the only surviving record "
 "of what that drive's control interface could do:\n\n"
 "  row 1:  24V  10V  AI1  GND  DI1  DI2  DI3  DI4  DI5\n"
 "  row 2:  TA   TB   TC   AOV  AOI  GND  FM   A+   B-\n\n"
 "  24V / 10V   auxiliary supplies; the 10 V rail is what feeds a speed pot\n"
 "  AI1         analog speed reference in\n"
 "  DI1-DI5     digital inputs — run/stop, direction, multi-speed, fault reset\n"
 "  TA/TB/TC    relay contacts, common / NO / NC, normally the fault relay\n"
 "  AOV / AOI   analog output, voltage and current flavours\n"
 "  FM          frequency-meter pulse output\n"
 "  A+ / B-     RS485 — so that drive spoke Modbus\n\n"
 "That is a generic VFD control layout, not a proprietary one, which is why the "
 "pinout is worth keeping: it reads the same on most small drives and makes a "
 "usable reference for wiring the next one.\n\n"
 "VFD teardown: fan #1078 (B3-R5C3), bus caps #1076 (A3-R7C5), barrier terminals "
 "#1079 and #1081 (A3-R7C4), heatsink #1077 still pending a hole-spacing "
 "measurement. Relay and IGBTs were scrap — all six heatsink IGBTs tested short.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.get(name__iexact=BIN)
if Part.objects.filter(name=NAME).exists():
    sys.exit("!! already exists")
cat = PartCategory.objects.filter(name__iexact="Connectors").first() \
    or PartCategory.objects.filter(name__icontains="connector").first()
print(f"{NAME}\n  -> {loc.pathstring}, qty {QTY}, category {cat}")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

p = Part.objects.create(name=NAME, description=DESC, category=cat,
                        purchaseable=False, component=True, active=True)
s = StockItem.objects.create(part=p, location=loc, quantity=QTY,
                             notes=f"TALLIED {TODAY}: one, off the VFD control board.")
Part.objects.filter(pk=p.pk).update(notes=NOTES, default_location=loc)
StockItem.objects.filter(pk=s.pk).update(stocktake_date=TODAY)
d = loc.description or ""
if "odd-pitch" not in d:
    StockLocation.objects.filter(pk=loc.pk).update(
        description=d.rstrip().rstrip(".") + ". Also odd-pitch PCB terminal "
        "oddments that do not earn their own drawer — currently one 3.5mm 18-way "
        "off the VFD control board, which will NOT mate with the 5.08mm parts.")
f = StockItem.objects.get(pk=s.pk)
assert float(f.quantity) == QTY and f.stocktake_date == TODAY, "stock did not stick"
assert Part.objects.get(pk=p.pk).default_location_id == loc.pk, "home did not stick"
assert "A+" in Part.objects.get(pk=p.pk).notes, "pinout did not stick"
assert "odd-pitch" in StockLocation.objects.get(pk=loc.pk).description, "bin desc"
print(f"\nOK  part #{p.pk}, stock #{f.pk} in {loc.name}, pinout recorded")
