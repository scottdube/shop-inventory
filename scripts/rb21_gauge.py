"""RB-21: the MEANLIN dial gauge, part of the Vacuum Controller project.

Which makes the Vacuum Controller the SECOND project to span two red bins
(RB-17 holds its MPXV6115VC6U sensor), so both descriptions name the other --
the RB-07/RB-08 convention.

The box gives accuracy, mount, temperature range and medium, and does NOT give
the pressure RANGE, which is the one spec that decides whether this gauge can
read vacuum at all. Recorded as unknown rather than inferred from the project
it was found next to.
"""
import os, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part, PartCategory
from stock.models import StockItem, StockLocation

COMMIT = "--commit" in sys.argv
TODAY = date.today()
user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()

NAME = "Pressure Gauge, 3in dial, lower mount, MEANLIN XJ-087"
DESC = ("MEANLIN MEASURE 3in dial gauge, lower (bottom) mount. Accuracy "
        "+/-3-2-3% (ASME B40.1 Grade B). Media: water, oil, air. Service temp "
        "32-131F / 0-55C. SKU XJ-087, ASIN X002SLRYVX. RANGE NOT ON THE BOX - "
        "read the dial before using it for anything.")
NOTE = (
    f"In RB-21, boxed and NEW, reported by Scott {TODAY} during the Red Bin "
    "walk as part of the VACUUM CONTROLLER project. Counted at 1: one sealed "
    "box, his figure.\n\n"
    "THE RANGE IS UNKNOWN AND IT IS THE SPEC THAT MATTERS. The box face carries "
    "accuracy, mount, medium and service temperature, and no pressure range. A "
    "vacuum controller needs a compound or vacuum dial (negative side); a "
    "general-service gauge reading 0-N psi cannot show vacuum at all. This is "
    "the same split already recorded on #107, whose MPXV6115VC6U reads 0 to "
    "-115 kPa and is NOT interchangeable with the positive-pressure 1/8 NPT "
    "transducers in B3-R7C2. Being found in the vacuum project's bin is not "
    "evidence of which half of the scale it reads - READ THE DIAL.\n\n"
    "Thread size also unread; the box says lower mount but not the NPT size."
)

dupes = (Part.objects.filter(name__icontains="meanlin")
         | Part.objects.filter(name__icontains="XJ-087")
         | Part.objects.filter(description__icontains="X002SLRYVX"))
print(f"duplicate check: {dupes.count()}")
for p in dupes:
    print(f"  #{p.pk} {p.name}")

print(f"\npart: {NAME!r}  desc {len(DESC)} chars")

RB21 = ("VACUUM CONTROLLER project, part 2 of 2 - the MEANLIN 3in dial gauge "
        "(#{pk}), boxed and new. The project's MPXV6115VC6U sensor is in RB-17. "
        "GAUGE RANGE IS UNREAD: the box gives accuracy, mount, medium and temp "
        "but no range, and a positive-only dial cannot read vacuum. Read the "
        "dial before designing around it.")
RB17_ADD = (" SECOND BIN: the project's MEANLIN 3in dial gauge is in RB-21 "
            "(Scott, 2026-08-25). One project across two bins, like RB-07/RB-08 "
            "- consolidating into one would free a bin.")

if not COMMIT:
    print("\n  DRY RUN - add --commit")
    sys.exit()

part = Part.objects.filter(name=NAME).first()
if part is None:
    part = Part.objects.create(
        name=NAME, description=DESC,
        category=PartCategory.objects.get(pathstring="Electronics/Test & Measurement"),
        purchaseable=True, active=True)
    print(f"created part #{part.pk}")

if StockItem.objects.filter(part=part).exists():
    sys.exit("stock row already exists - look first")
rb21 = StockLocation.objects.get(name="RB-21")
si = StockItem.objects.create(part=part, location=rb21, quantity=1, notes=NOTE)
StockItem.objects.filter(pk=si.pk).update(stocktake_date=TODAY, stocktake_user=user)

rb21_desc = RB21.format(pk=part.pk)
StockLocation.objects.filter(pk=rb21.pk).update(description=rb21_desc)
rb17 = StockLocation.objects.get(name="RB-17")
StockLocation.objects.filter(pk=rb17.pk).update(description=rb17.description + RB17_ADD)

si = StockItem.objects.get(pk=si.pk)
print(f"\nstock #{si.pk} qty={si.quantity:g} @ {si.location.pathstring} stocktake={si.stocktake_date}")
print("  RB-21:", "OK" if StockLocation.objects.get(pk=rb21.pk).description == rb21_desc else "MISMATCH")
print("  RB-17:", "OK" if StockLocation.objects.get(pk=rb17.pk).description.endswith(RB17_ADD) else "MISMATCH")
