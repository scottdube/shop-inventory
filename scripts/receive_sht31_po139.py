"""Receive PO-0139: one Amazon pack of 4 SHT31-D breakouts, split 2 + 2.

Two of the four go to RB-12 (the RAT GDO project kit, BO-0009); two go to the
part's default_location B3-R4C8 as spares -- a project bin is not where a spare
goes home.

The line is repaired first. It was auto-created from the Amazon confirmation as
qty=1 @ $16.99, but the ASIN is a 4-piece pack and supplier part 193 carries
pack_quantity=1. Receiving it unrepaired would have booked ONE sensor at $16.99
-- the same pack-price-per-piece error that made 19 storage bins read $208.62.

Repaired by rewriting the LINE (4 @ $4.2475), not by setting pack_quantity=4 on
the supplier part: pack_quantity is read at receive time, so changing it would
retroactively reread PO-0028's completed 4-unit receipt as 16 pieces.

The four pieces from PO-0028 (stock 573, 574) are deliberately NOT touched.
They are owned-but-location-unknown and are a separate open question; folding
them into this receipt would launder a real uncertainty into a tidy number.
"""
import argparse, os, sys, django
from decimal import Decimal

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from djmoney.money import Money
from order.models import PurchaseOrder, PurchaseOrderLineItem
from stock.models import StockLocation, StockItem

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

PIECES = 4
UNIT = Decimal("4.2475")          # 16.99 / 4, the grand total off the order page
SPLIT = [("RB-12", 2), ("B3-R4C8", 2)]

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
po = PurchaseOrder.objects.get(reference="PO-0139")
line = po.lines.get(pk=161)

print(f"PO {po.reference} status={po.get_status_display()} supplier_ref={po.supplier_reference}")
print(f"line {line.pk}: qty={line.quantity:g} @ {line.purchase_price} received={line.received:g}")
print(f"  supplier part {line.part.pk} SKU={line.part.SKU} pack_quantity={line.part.pack_quantity}")

dests = {}
for name, n in SPLIT:
    loc = StockLocation.objects.filter(name=name).first()
    if not loc:
        sys.exit(f"no such location: {name}")
    dests[name] = loc
    print(f"  {n} -> {loc.pathstring}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

# --- repair the line ------------------------------------------------------
# .save() on this install has reported success and written nothing, so the
# write goes through the queryset and is read back before anything depends on it.
PurchaseOrderLineItem.objects.filter(pk=line.pk).update(
    quantity=PIECES,
    purchase_price=UNIT,
    notes=(line.notes or "").strip() + (
        "\n\nLINE REPAIRED 2026-08-26 at receiving. Was qty=1 @ $16.99: the "
        "confirmation sweep booked the pack price against a single piece. "
        "B0B5TN8LZB is a 4-piece pack, so this is 4 @ $4.2475 ($16.99 total, "
        "grand total from the order-details page). pack_quantity on supplier "
        "part 193 left at 1 on purpose -- raising it would retroactively "
        "reread PO-0028's completed 4-unit receipt as 16 pieces."
    ),
)
line.refresh_from_db()
print(f"\nline after repair: qty={line.quantity:g} @ {line.purchase_price}")
if float(line.quantity) != PIECES:
    sys.exit("line quantity did not stick -- stopping before any stock is created")

# --- receive --------------------------------------------------------------
for name, n in SPLIT:
    po.receive_line_item(line, dests[name], n, user)
    print(f"received {n} -> {name}")

# --- annotate the rows this created ---------------------------------------
NOTE = {
    "RB-12": (
        "Received 2026-08-26 against PO-0139 (Amazon 113-5011479-9313006), one "
        "pack of 4 counted in hand by Scott. Two of the four to the RAT GDO "
        "project kit, BO-0009.\n\nThis is the live RB-12 stock. Stock 341 is the "
        "spent history of the 2026-06-28 purchase and stays at zero."
    ),
    "B3-R4C8": (
        "Received 2026-08-26 against PO-0139 (Amazon 113-5011479-9313006), one "
        "pack of 4 counted in hand by Scott. The two SPARES, to the part's "
        "default_location.\n\nNOT the same parts as stock 573/574. Those are the "
        "PO-0028 four, still owned-but-location-unknown since 2026-08-23; if "
        "they turn up, they merge into this row."
    ),
}
for si in StockItem.objects.filter(purchase_order=po, part_id=292):
    key = si.location.name if si.location else None
    if key in NOTE:
        StockItem.objects.filter(pk=si.pk).update(notes=NOTE[key])

# --- forward-pointer on the zero history row ------------------------------
old = StockItem.objects.filter(pk=341).first()
if old and float(old.quantity) == 0:
    StockItem.objects.filter(pk=341).update(
        notes=(old.notes or "").rstrip() + (
            "\n\n2026-08-26: the live RB-12 stock is now the PO-0139 row, not the "
            "PO-0028 rows named above -- those (573, 574) lost their location on "
            "2026-08-23 and are still unlocated. This row remains at zero."
        )
    )

# --- close it out ---------------------------------------------------------
line.refresh_from_db()
if float(line.received) >= float(line.quantity):
    po.complete_order()

# --- verify ---------------------------------------------------------------
po.refresh_from_db()
line.refresh_from_db()
print(f"\nPO {po.reference}: {po.get_status_display()}  line received={line.received:g}/{line.quantity:g}")
print("\nall stock for part 292:")
total = 0
for si in StockItem.objects.filter(part_id=292).order_by("pk"):
    total += float(si.quantity)
    print(f"  [{si.pk}] {si.quantity:g} @ {si.location.name if si.location else 'UNLOCATED'}"
          f"  po={si.purchase_order}  price={si.purchase_price}")
print(f"  total on books: {total:g}")
