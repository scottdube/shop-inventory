"""Locate the dash-135 Viton O-rings to A2-R4C2, and print our own label.

Scott 2026-08-26: "I think that's from the manufacturer... I think McMaster
relabeled it. So we'll just need a new label of our own for that so that we can
identify it."

MCMASTER STOCK DOES NOT ALWAYS ARRIVE IN A MCMASTER BAG. The three washer bags
earlier today carried McMaster's own printed label ("McMaster Carr Supply /
609-223-4039") and this one does not -- it is the maker's bag, "75 VITON / SIZE
- 135 / QTY - 10 / CAA086", with a California P65 warning. On that basis I
argued it was a different vendor's part and that #1004 was still missing.

Wrong, and worth writing down: McMaster resells manufacturer-packaged goods,
sometimes with their own label over the top and sometimes without. **Packaging
style is not evidence of vendor.** The part number, size and pack quantity are.
Dash 135, 3/32 width, pack of 10, and PO-0122 bought exactly that.

So stock 505 is located, not missing -- the third McMaster row today whose
"unknown location" turned out to mean the record never knew.

FILED TO A2-R4C2, which already exists for exactly this: "Seals — Viton (FKM)
O-rings and sealing washers. Separate from the steel washers at R4C1 on purpose:
a seal keeps fluid in, a washer spreads load, and they are not substitutes.
ROOM REMAINS." It already holds the Viton sealing washer #1003 from the SAME
PO-0122.

QUANTITY LEFT AS [ESTIMATE], unlike the washers. Ten is a five-second count and
the bag's seal state is unconfirmed, so the marker promises a check that can
actually be redeemed. A hundred washers was the opposite case.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

cell = StockLocation.objects.get(name="A2-R4C2")
si = StockItem.objects.get(pk=505)
p = Part.objects.get(pk=1004)
print(f"[{p.pk}] {p.name}")
print(f"  stock[{si.pk}] qty={si.quantity:g} from {si.location or 'UNLOCATED'} -> {cell.pathstring}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

si.location = cell
si.save()
StockItem.objects.filter(pk=505).update(notes=(
    "LOCATED 2026-08-26 to A2-R4C2, the seals cell. Photographed on the bench "
    "by Scott in the MAKER'S bag: '75 VITON / SIZE - 135 / QTY - 10 / CAA086', "
    "with a P65 warning and no McMaster branding.\n\n"
    "That bag was briefly argued to be a different vendor's, because the three "
    "McMaster washer bags the same afternoon carried McMaster's own printed "
    "label. Scott: McMaster relabels manufacturer packaging. **Packaging style "
    "is not evidence of vendor** — the size, width and pack quantity are, and "
    "dash 135 / 3/32 / pack of 10 is exactly what PO-0122 bought.\n\n"
    "[ESTIMATE] Quantity 10 is the bag figure, not a count, and the seal state "
    "is unconfirmed. Kept as an estimate deliberately: ten is a five-second "
    "count, so this marker promises a check that can actually be redeemed. The "
    "hundred-piece washer bags were the opposite case and were accepted "
    "outright."))
Part.objects.filter(pk=1004).update(default_location=cell,
    notes=(p.notes or "").rstrip() +
    "\n\nARRIVED IN THE MAKER'S BAG, NOT A MCMASTER ONE — '75 VITON / SIZE - "
    "135 / QTY - 10 / CAA086'. McMaster resells manufacturer-packaged goods, so "
    "an unbranded bag is not evidence the part came from somewhere else. Ours "
    "is the label that makes it identifiable on the shelf.\n\n"
    "75 durometer, per the bag. Dash 135 in the AS568 100-series: 3/32 in "
    "nominal cross-section, 1.925 in nominal ID.")

si.refresh_from_db()
print(f"  now: {si.quantity:g} @ {si.location.pathstring}")
print(f"  cell holds {StockItem.objects.filter(location=cell).count()} rows")
print(f"  unlocated rows with stock: "
      f"{StockItem.objects.filter(location__isnull=True, quantity__gt=0).count()}")
