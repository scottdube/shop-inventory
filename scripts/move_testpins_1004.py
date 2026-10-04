"""Move the PO-0184 test point pins (SI 902) from B0-R1C3 to A3-R7C7, 2026-10-04.

Scott: "the test points can go to a3 r7 c7" -- filing them with the barrel
jacks was my misreading of "with the b jacks". Whole-row move via
StockItem.move() so the tracking history records it; the florida earmark
lives in the row's metadata and travels with it. Home follows the stock.

    itq run scripts/move_testpins_1004.py            # dry run
    itq run scripts/move_testpins_1004.py --commit
"""
import os, sys, django
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings"); django.setup()
from django.contrib.auth import get_user_model
from part.models import Part
from stock.models import StockItem, StockLocation
dest = StockLocation.objects.get(name="A3-R7C7")
si = StockItem.objects.get(pk=902)
here = list(StockItem.objects.filter(location=dest).values_list("part__name", "quantity"))
print(f"dest {dest.pathstring} labeled={(dest.metadata or {}).get('labeled')} desc={dest.description!r}")
print(f"   recorded rows there: {here}  (0 rows = unrecorded, not empty)")
print(f"SI 902 {si.part.name[:45]} qty {si.quantity} @ {si.location.pathstring}")
if "--commit" not in sys.argv:
    sys.exit("\nDRY RUN -- add --commit")
user = get_user_model().objects.filter(is_superuser=True).first()
si.move(dest, "Scott 2026-10-04: test pins live in A3-R7C7, not with the barrel jacks", user)
Part.objects.filter(pk=si.part_id).update(default_location=dest)
# the old text says VERIFIED EMPTY, which stops being true the moment this lands
StockLocation.objects.filter(pk=dest.pk).update(description=(
    "PCB TEST POINT PINS - black, 3.2 mm head, 0.8-1.0 mm hole (PO-0184, filed "
    "2026-10-04 by Scott). [6 x 2-7/32 x 1-9/16 in, small]"))
si = StockItem.objects.get(pk=902)
print(f"re-read: SI 902 qty {si.quantity} @ {si.location.pathstring} | home {si.part.default_location.pathstring} | fl {si.metadata.get('florida')}")
print("dest desc:", StockLocation.objects.get(pk=dest.pk).description)
print("rows for part 1264:", list(StockItem.objects.filter(part_id=1264).values_list("pk", "quantity", "location__name")))
