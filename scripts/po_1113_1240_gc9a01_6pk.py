"""Queue C, 12:40 daytime sweep 2026-11-13: one Amazon order -> one PLACED PO.

  order                 ASIN        qty x pack price  arrives
  113-4438996-4049024   B0GZ2KMYMZ  3 x  6    25.99  "Arriving Sunday" (11-15)

Placed 2026-11-13, ships to The Villages FL (LRD). Price is the item line on the order-details
page read in Chrome 2026-11-13 12:4x: two shipment blocks of the same ASIN (qty 2 and qty 1),
each line $25.99; subtotal $77.97 = 3 x 25.99, shipping $0, tax $5.46, grand total $83.43.
Sold by Aceirmc US. Same listing as PO-0292 (113-3911830-6571465, 5 packs, 2026-11-11):
"6pcs 1.28 Inch 1.28'' TFT LCD Display Module Round RGB 240 * 240 GC9A01 Driver 4 Wire SPI
Interface 240x240 PCB for Arduino Nano STM32" -> pack 6, counted in displays (3 x 6 = 18).

One PO line of qty 3, not two lines of 2 and 1: the split on the page is Amazon's shipment
grouping of one ASIN at one price, not two different items.

The supplier part for B0GZ2KMYMZ already exists (made by po_1111_1640_gc9a01_6pk.py); this
script REQUIRES it and never creates a part or a supplier part.

Dry run by default; --commit writes. PLACED, never received.
"""
import argparse
import datetime
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402
from plugins.notes_compat import note_set, note_text  # noqa: E402

RUN = "12:40 daytime sweep 2026-11-13"
ORDER = "113-4438996-4049024"
ASIN = "B0GZ2KMYMZ"
QTY, PRICE, PACK = 3, "25.99", 6
ISSUE = datetime.date(2026, 11, 13)
ARRIVE = datetime.date(2026, 11, 15)
SP_DESC = "Aceirmc 1.28in round TFT GC9A01 240x240 SPI display module, 6 pcs"

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

sps = list(SupplierPart.objects.filter(supplier=amazon, SKU__iexact=ASIN))
for s in sps:
    print(f"  sp #{s.pk} {s.SKU!r} -> part #{s.part_id} active={s.part.active} {s.part.name!r} "
          f"pack={s.pack_quantity}/{s.pack_quantity_native}")
    for li in PurchaseOrderLineItem.objects.filter(part=s):
        print(f"      on {li.order.reference} ({li.order.supplier_reference}) qty={li.quantity} "
              f"@ {li.purchase_price} status={li.order.status}")
dup = PurchaseOrder.objects.filter(Q(supplier_reference=ORDER) | Q(reference=ORDER))
print(f"{ORDER}: existing={[(p.reference, p.lines.count()) for p in dup]}")

assert len(sps) == 1, f"expected exactly one Amazon supplier part for {ASIN}, found {len(sps)}"
sp = sps[0]
assert sp.part.active, "supplier part points at an inactive part"
assert "GC9A01" in (sp.part.name + (sp.part.description or "")), "not a GC9A01 part"
assert float(sp.pack_quantity_native) == float(PACK), f"pack native is {sp.pack_quantity_native}"

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --commit")

if dup.exists():
    assert dup.count() == 1
    po = dup.first()
    if po.lines.count():
        raise SystemExit(f"SKIP {ORDER}: {po.reference} already has lines")
    print(f"RESUMING {po.reference} (0 lines)")
else:
    po = PurchaseOrder(supplier=amazon, reference=PurchaseOrder.generate_reference(),
                       supplier_reference=ORDER,
                       description=f"Amazon order {ORDER} — {SP_DESC} x{QTY} (to The Villages FL)",
                       issue_date=ISSUE, target_date=ARRIVE,
                       status=PurchaseOrderStatus.PLACED.value)
    po.save()
    po.refresh_from_db()
assert po.supplier_id == amazon.pk and po.supplier_reference == ORDER
assert po.status == PurchaseOrderStatus.PLACED.value and po.reference != ORDER
note_set(po, f"Auto-created by the queue C daytime sweep, {RUN}.\n\nShips to The Villages FL (LRD).\n\n"
             f"Line price read from the Amazon order-details page: 3 x $25.99 (shown as two shipment "
             f"blocks, qty 2 and qty 1, same ASIN), subtotal $77.97, shipping $0.00, tax $5.46, "
             f"grand total $83.43.\n\nLine is in packs of {PACK} at the pack price; supplier part "
             f"{ASIN} carries pack_quantity {PACK}, so receive_po.py books 18 displays.\n\n"
             f"Same listing as PO-0292 (5 packs, 2026-11-11).\n\nPLACED, not received.")
assert note_text(po).startswith("Auto-created"), "PO note did not stick"
li = PurchaseOrderLineItem(order=po, part=sp, quantity=QTY,
                           purchase_price=PRICE, purchase_price_currency="USD")
li.save()
li.refresh_from_db()
assert float(li.quantity) == QTY and float(li.purchase_price.amount) == float(PRICE)
po.refresh_from_db()
print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
      f"target={po.target_date} lines={po.lines.count()} ({QTY} x sp #{sp.pk} @ {PRICE})")
