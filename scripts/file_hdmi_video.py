"""HDMI video set into B3-R5C1, and broaden that bin from 'round' to 'displays'.

Scott 2026-08-28: "This stuff is currently homeless, so we can put it wherever.
Maybe one of the larger boxes on the wall bins."

B3-R5C1 rather than a fresh large bin, deliberately. Its own description already
warns "CHARACTER LCDs are still at A3-R2C5 -- check BOTH when asking what
displays the shop has." Opening a third display location would make that warning
worse. Putting these here means the count of places to look stays at two.

The bin was named GRAPHIC / ROUND DISPLAYS. Broadened, because 'round' was
describing today's contents rather than the drawer's job -- and a name that
narrow is how the next rectangular panel ends up somewhere else.
"""
import argparse, datetime, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory                       # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

BIN, TODAY = "B3-R5C1", datetime.date.today()
BRIDGE = 726

NEW_NAME = "waveshare 4inch HDMI Display-C, 800x480 IPS, XPT2046 resistive touch"
NEW_DESC = ("waveshare 4inch HDMI Display-C. 800x480 IPS panel, HDMI video in, "
            "XPT2046 resistive touch over USB, backlight control header. Blue "
            "PCB, CE/RoHS marked.")
NEW_NOTES = (
 f"TALLIED {TODAY}: one, in hand.\n\n"
 "TOUCH IS RESISTIVE AND SEPARATE FROM VIDEO. XPT2046 is a resistive controller "
 "-- stylus or fingernail, one point, needs calibrating. It rides over USB while "
 "the picture arrives over HDMI, so this display needs TWO cables to be useful "
 "and half-wiring it gives a picture that ignores you.\n\n"
 "NOT a Pi DSI display and not a Pi HAT: it is a generic HDMI monitor that "
 "happens to be 4 inches, so it works with anything that outputs HDMI at "
 "800x480. That is its advantage over the DSI panels and worth remembering "
 "before someone buys another.\n\n"
 "A FAN WAS SITTING ON THIS BOARD in the 2026-08-28 photo (YCCFAN YDL3007C0E, "
 "5V 0.12A) -- it belongs to a case or another assembly, not to the display. Not "
 "catalogued as part of this item.\n\n"
 "Opposite direction from the HDMI-to-CSI bridge (#726) in this same bin: the "
 "bridge takes HDMI IN to a Pi camera port, this takes HDMI OUT to a screen. "
 "They share a drawer and a connector family, not a purpose.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.get(name__iexact=BIN)
b = Part.objects.get(pk=BRIDGE)
print(f"bin {loc.pathstring} — {StockItem.objects.filter(location=loc).count()} rows")
print(f"  #{b.pk} {b.name[:56]}  stock={float(b.total_stock):g}")
print(f"  NEW: {NEW_NAME[:56]}")
if StockItem.objects.filter(part=b).exists():
    sys.exit("!! bridge already has stock")
if Part.objects.filter(name=NEW_NAME).exists():
    sys.exit("!! display part already exists")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# 1. the bridge finally gets a stock row
sb = StockItem.objects.create(part=b, location=loc, quantity=1,
    notes=f"TALLIED {TODAY}: one, with its 15-pin FFC ribbon. Catalogued since "
          "import with no stock row until now.")
StockItem.objects.filter(pk=sb.pk).update(stocktake_date=TODAY)
Part.objects.filter(pk=BRIDGE).update(default_location=loc)
assert StockItem.objects.get(pk=sb.pk).stocktake_date == TODAY
print(f"OK  #{BRIDGE} stock #{sb.pk} qty=1")

# 2. the display
cat = PartCategory.objects.filter(name__icontains="display").first() \
      or Part.objects.get(pk=BRIDGE).category
p = Part.objects.create(name=NEW_NAME, description=NEW_DESC, category=cat,
                        purchaseable=True, component=True, active=True)
sd = StockItem.objects.create(part=p, location=loc, quantity=1,
                              notes=f"TALLIED {TODAY}: one, in hand. Untested.")
Part.objects.filter(pk=p.pk).update(notes=NEW_NOTES, default_location=loc)
StockItem.objects.filter(pk=sd.pk).update(stocktake_date=TODAY)
assert StockItem.objects.get(pk=sd.pk).stocktake_date == TODAY
assert Part.objects.get(pk=p.pk).default_location_id == loc.pk
print(f"OK  part #{p.pk} stock #{sd.pk} qty=1")

# 3. the bin outgrows its name
d = loc.description
nd = d.replace("GRAPHIC / ROUND DISPLAYS.",
    "GRAPHIC DISPLAYS & HDMI VIDEO. Renamed from 'ROUND' 2026-08-28 — that was "
    "describing the contents, not the drawer's job, and a name that narrow is "
    "how the next rectangular panel lands somewhere else. Now also holds the "
    "waveshare 4inch HDMI Display-C and the HDMI-to-CSI bridge (#726), which "
    "point in OPPOSITE directions: the bridge takes HDMI in to a Pi camera "
    "port, the display takes HDMI out to a screen.")
StockLocation.objects.filter(pk=loc.pk).update(description=nd[:1000])
assert "HDMI VIDEO" in StockLocation.objects.get(pk=loc.pk).description
print("OK  bin renamed and re-described")
