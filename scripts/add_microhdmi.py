"""Micro-HDMI to HDMI adapter into B3-R5C1. Measured, not guessed.

Scott measured the plug at 6 mm 2026-08-28. Micro-HDMI (Type D) is 6.4 mm wide,
mini-HDMI (Type C) is 10.4 mm -- nearly a factor of two, so one caliper reading
settles what two photographs could not.

That rules out #265 (QimKero Mini HDMI to HDMI, 2-pack), which stays at zero
stock and is a genuinely different connector.
"""
import argparse, datetime, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory                       # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

BIN, QTY, TODAY = "B3-R5C1", 1, datetime.date.today()
NAME = "Adapter Cable, micro-HDMI (Type D) male to HDMI (Type A) female, ~150mm"
DESC = ("Short micro-HDMI to full-size HDMI adapter pigtail. Micro-HDMI Type D "
        "male one end, HDMI Type A female the other, roughly 150 mm of cable "
        "with strain relief.")
NOTES = (
 f"TALLIED {TODAY}: one, in hand.\n\n"
 "TYPE CONFIRMED BY MEASUREMENT, not by eye. Scott read the plug at 6 mm on "
 "calipers 2026-08-28. Micro-HDMI (Type D) is 6.4 mm wide and mini-HDMI (Type C) "
 "is 10.4 mm — nearly a factor of two, which is why measuring settles instantly "
 "what two photographs could not. The two do NOT interchange and look similar "
 "enough in a drawer to be grabbed for each other.\n\n"
 "NOT #265. That part is the QimKero MINI HDMI to HDMI 2-pack, still at zero "
 "stock, and it is a different connector. If somebody needs a mini adapter this "
 "is not it.\n\n"
 "MICRO-HDMI IS THE RASPBERRY PI 4 AND 5 CONNECTOR. Those boards carry two "
 "micro-HDMI ports and ship with no adapter, so this is the cable that makes the "
 "Pi 4 (#1094, RB-11) usable on an ordinary monitor. Worth knowing before "
 "somebody buys another.\n\n"
 "Filed with the displays and HDMI video rather than with cables, because the "
 "question that finds it is \"how do I get a picture out of this\", not \"where "
 "are the cables\".")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.get(name__iexact=BIN)
if Part.objects.filter(name=NAME).exists():
    sys.exit("!! already exists")
cat = (PartCategory.objects.filter(name__icontains="cable").first()
       or PartCategory.objects.filter(name__icontains="connector").first())
print(f"{NAME}\n  -> {loc.pathstring}, qty {QTY}, category {cat}")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

p = Part.objects.create(name=NAME, description=DESC, category=cat,
                        purchaseable=True, component=True, active=True)
s = StockItem.objects.create(part=p, location=loc, quantity=QTY,
                             notes=f"TALLIED {TODAY}: one, in hand. Plug measured "
                                   "at 6 mm — micro-HDMI Type D, not mini.")
Part.objects.filter(pk=p.pk).update(notes=NOTES, default_location=loc)
StockItem.objects.filter(pk=s.pk).update(stocktake_date=TODAY)
f = StockItem.objects.get(pk=s.pk)
assert float(f.quantity) == QTY and f.stocktake_date == TODAY, "stock did not stick"
assert Part.objects.get(pk=p.pk).default_location_id == loc.pk, "home did not stick"
print(f"\nOK  part #{p.pk}, stock #{f.pk} qty=1 in {loc.name}")
