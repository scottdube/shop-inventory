"""Two of the 47 unlocated rows are FOUND: the M5 and M6 flat washers.

Scott photographed both McMaster bags 2026-08-26 and confirmed both are SEALED.

  #1037 / stock 538  98687A110  M5 flat washer, 5.5 ID x 10 OD   100 PCS
  #1038 / stock 539  98687A111  M6 flat washer, 6.6 ID x 12 OD   100 PCS

Both bought on PO-0130, issued 2022-02-01 -- the same McMaster order as the
ANSI 35 sprocket and the 3/8" nylon sleeve bearing. So that order was part
machine-build, part restock, which is worth knowing before the rest of it gets
attributed to a project wholesale.

QUANTITY IS TIER-4 ACCEPTED: 100, from the bag, no [ESTIMATE] marker and no
stocktake_date. The bags are sealed and nobody is ever going to count a hundred
washers, so an ESTIMATE marker here would be a promise of a check that never
comes -- and a marker that never comes off teaches people to ignore markers.
The null stocktake_date still correctly says nobody counted them.

Contrast the LM8UU bag this morning: label said 12, bench said 10, because that
bag was OPEN. Sealed is the whole difference, which is why it was asked.

FILED TO B1, THE METRIC FASTENER CABINET -- not to the Bearings & Motion bin
they arrived with, and not to A2-R8C8. A2-R8C8's own description says
"PRE-SORT QUEUE, not a home", which is the opposite of what it was recommended
for earlier today; the name said hardware and the record said queue.

Filed at cabinet level rather than a numbered cell because no cell has been
chosen. B1 already holds 26 rows that way. A cell later is a re-parent.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
b1 = StockLocation.objects.get(name="B1")
ROWS = {538: ("M5", "98687A110"), 539: ("M6", "98687A111")}

for pk, (size, sku) in ROWS.items():
    si = StockItem.objects.get(pk=pk)
    print(f"[{pk}] {si.quantity:g} x {size} washer  loc={si.location or 'UNLOCATED'}")
print(f"-> {b1.pathstring}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

for pk, (size, sku) in ROWS.items():
    si = StockItem.objects.get(pk=pk)
    si.location = b1
    si.save()
    StockItem.objects.filter(pk=pk).update(notes=(
        f"FOUND 2026-08-26. Photographed on the bench by Scott, McMaster bag "
        f"{sku}, SEALED, label reads 100 PCS.\n\n"
        f"This row had location=NULL since the McMaster import -- owned, "
        f"whereabouts unknown. It is one of the 47 such rows, and the second of "
        f"them to be resolved by a bag physically turning up.\n\n"
        f"QUANTITY 100 IS TIER-4 ACCEPTED, not an estimate: the bag is sealed "
        f"and nobody will ever count a hundred washers. No marker. The null "
        f"stocktake_date still says, correctly, that nobody counted them.\n\n"
        f"Filed to B1 at cabinet level; no numbered cell chosen yet. Moving it "
        f"to one is a re-parent, not a re-entry."))
    Part.objects.filter(pk=si.part_id).update(default_location=b1)

print("\nverify:")
for pk in ROWS:
    si = StockItem.objects.get(pk=pk)
    print(f"  [{pk}] {si.quantity:g} @ {si.location.pathstring if si.location else 'STILL UNLOCATED'} "
          f"stocktake={si.stocktake_date} dl={si.part.default_location}")

rem = StockItem.objects.filter(location__isnull=True, quantity__gt=0).count()
print(f"\nunlocated rows with stock remaining: {rem}")
