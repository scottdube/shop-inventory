"""Receive PO-0140 - the MFC Tormach Z-axis way cover Scott says has arrived.

Lands in SLN/Receiving, the established landing spot (#472), NOT in a drawer and
NOT with a stocktake_date. Per docs/TRAPS.md ("A put-away done by a person IS a
count - a PO receipt never is"), Scott saying the box is here proves the order
ARRIVED. It does not prove where the thing now lives, and recording a
destination nobody has carried it to is exactly the SHT31 failure.

The put-away is the next, separate act, and it is the one that earns a
stocktake_date. If the cover goes straight onto the mill it should not become a
drawer row at all - scripts/into_service.py and belongs_to are the mechanism,
because stock means SPARES and a cover bolted to the 1100MX is not a spare.

Uses InvenTree's own receive_line_item so pack conversion and history behave.
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth import get_user_model      # noqa: E402
from order.models import PurchaseOrder              # noqa: E402
from stock.models import StockItem, StockLocation   # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()
DRY = not a.commit

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
po = PurchaseOrder.objects.get(reference="PO-0140")
dest = StockLocation.objects.get(pk=472)
assert dest.pathstring == "SLN/Receiving", dest.pathstring

print(f"PO {po.reference} supplier_ref={po.supplier_reference} status={po.get_status_display()}")
print(f"dest = {dest.pathstring}")

line = po.lines.first()
assert line is not None, "PO-0140 has no lines"
print(f"line qty={line.quantity} already_received={line.received}")

if line.received >= line.quantity:
    print("SKIP: already fully received")
    sys.exit(0)

qty = line.quantity - line.received
print(f"receiving qty={qty}")

if DRY:
    print("\nDRY RUN - nothing written")
    sys.exit(0)

po.receive_line_item(line, dest, qty, user)

fresh_line = po.lines.first()
po.refresh_from_db()
print(f"+ line received={fresh_line.received}  PO status={po.get_status_display()}")

items = StockItem.objects.filter(part__pk=1085)
assert items.exists(), "no stock row created - receive did not stick"
for s in items:
    note = ("ARRIVED 2026-08-24, confirmed by Scott. This is a RECEIPT, not a put-away: "
            "it proves the order came, not where the cover now lives and not a count. "
            "No stocktake_date on purpose. Next act is the put-away - or, if it goes onto "
            "the 1100MX, scripts/into_service.py (belongs_to), since stock means spares "
            "and a fitted cover is not one.")
    StockItem.objects.filter(pk=s.pk).update(notes=note)
    f = StockItem.objects.get(pk=s.pk)
    assert f.notes.startswith("ARRIVED"), "stock note did not stick"
    print(f"  stock #{f.pk} qty={f.quantity} loc={f.location.pathstring if f.location else None} "
          f"stocktake={f.stocktake_date}")
