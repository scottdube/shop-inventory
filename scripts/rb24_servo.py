"""RB-24: the motorized water shutoff valve prototype.

One ANNIMOS 35KG servo (#242, the survivor of today's twin merge) plus 3D
printed mounting parts. Scott, 2026-08-25: "1 servo, 3d printed mounting parts,
prototyping a motorized water shutoff valve."

The prints get NO stock row, following RB-08's cord-retraction prototypes: a
shop-printed prototype is not stock, it is the current state of an experiment,
and giving it a quantity implies a spare that could be reprinted identically.
The bin description carries them instead, which is what DECLARED is for.
"""
import os, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part
from stock.models import StockItem, StockLocation

COMMIT = "--commit" in sys.argv
TODAY = date.today()
user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()

part = Part.objects.get(pk=242)
rb24 = StockLocation.objects.get(name="RB-24")

NOTE = (
    f"Counted at 1 by Scott {TODAY} during the Red Bin walk - one servo in "
    "RB-24, his figure.\n\n"
    "ALLOCATED to the MOTORIZED WATER SHUTOFF VALVE prototype, with 3D printed "
    "mounting parts in the same bin. A metal servo horn with a ball link is "
    "already fitted to the output shaft (seen in the photograph), so this is a "
    "servo in a mock-up, not a spare on a shelf.\n\n"
    "This part was the survivor of a merge the same day: #53 held the tidy name "
    "and the purchase note, #242 the ASIN, supplier part and image. The merge "
    "was done BEFORE this count so the number could not land on the wrong twin."
)
RB24 = ("MOTORIZED WATER SHUTOFF VALVE - prototype, being worked. One ANNIMOS "
        "35KG coreless digital servo (#242, horn and ball link already fitted) "
        "plus 3D PRINTED MOUNTING PARTS. The prints carry NO stock row on "
        "purpose - a prototype print is the state of an experiment, not stock, "
        "and a quantity would imply a spare. Same treatment as RB-08's cord "
        "retraction prototypes. No build order yet.")

print(f"#{part.pk} {part.name}")
print(f"  existing rows: {StockItem.objects.filter(part=part).count()}")
print(f"  would create qty 1 @ {rb24.pathstring}, stocktake {TODAY}")
print(f"  RB-24 desc: {len(RB24)} chars")

if not COMMIT:
    print("\n  DRY RUN - add --commit")
    sys.exit()

if StockItem.objects.filter(part=part).exists():
    sys.exit("stock row already exists - look first")
si = StockItem.objects.create(part=part, location=rb24, quantity=1, notes=NOTE)
StockItem.objects.filter(pk=si.pk).update(stocktake_date=TODAY, stocktake_user=user)
StockLocation.objects.filter(pk=rb24.pk).update(description=RB24)

si = StockItem.objects.get(pk=si.pk)
print(f"\n  stock #{si.pk} qty={si.quantity:g} @ {si.location.pathstring} "
      f"stocktake={si.stocktake_date}")
print("  RB-24:", "OK" if StockLocation.objects.get(pk=rb24.pk).description == RB24 else "MISMATCH")
