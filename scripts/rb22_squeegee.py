"""RB-22 holds the NEWISHTOOL squeegee pair -- which was already on the books,
filed at the RACK, not in a bin.

#791 sat at SLN/Electronics Bench/Red Bins with the note "Red bin at the
electronics bench" and no bin number: a cabinet-level filing, which claims a
place that does not exist. It was the only row on the rack itself. The walk
found the bin, so this is a LOCATE, not a new part -- creating one would have
made an import twin of a row that already had the count and the provenance.
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

si = StockItem.objects.get(pk=94)
rb22 = StockLocation.objects.get(name="RB-22")
print(f"stock #{si.pk} part#{si.part.pk} qty={si.quantity:g}")
print(f"  {si.location.pathstring} -> {rb22.pathstring}")

NOTE_ADD = (
    f"\n\n--- LOCATED {TODAY} ---\n"
    "Found in RB-22 during the Red Bin walk: two orange NEWISHTOOL-branded "
    "squeegee cards, photographed. Brand, count and 'red bin' all match this "
    "row, so it is the same pair - located, not re-counted, and no new part "
    "created. Before this the row sat at the RACK with no bin number, the only "
    "row on the rack itself; a cabinet-level filing claims a place that does "
    "not exist.\n\n"
    "MATERIAL IS IN DOUBT. The part description says 'soft silicone'; the two "
    "cards look like semi-rigid plastic in the photograph. Flex one - it is a "
    "one-second test - and fix the description. The name also says 'Screen "
    "Printing', which came from the listing; a stiff card is a solder-paste "
    "stencil / vinyl applicator squeegee, and a soft silicone one is not."
)
RB22 = ("Two NEWISHTOOL orange squeegee cards (#791), located here 2026-08-25. "
        "FREE STORAGE, not a project kit. Material in doubt: the record says "
        "soft silicone, the cards look semi-rigid - flex one and fix it. Loose "
        "hand tools belong on the wall, so this bin is a candidate to empty "
        "once they have a home.")

if not COMMIT:
    print("\n  DRY RUN - add --commit")
    sys.exit()

si.move(rb22, f"Located in RB-22 during the Red Bin walk (Scott, {TODAY}).", user)
StockItem.objects.filter(pk=si.pk).update(notes=si.notes + NOTE_ADD)
StockLocation.objects.filter(pk=rb22.pk).update(description=RB22)

si = StockItem.objects.get(pk=si.pk)
rack = StockLocation.objects.get(name="Red Bins")
left = StockItem.objects.filter(location=rack).count()
print(f"\n  stock #{si.pk} now @ {si.location.pathstring}")
print(f"  rows still filed at the rack itself: {left}")
print("  notes:", "OK" if si.notes.endswith(NOTE_ADD) else "MISMATCH")
print("  RB-22:", "OK" if StockLocation.objects.get(pk=rb22.pk).description == RB22 else "MISMATCH")
