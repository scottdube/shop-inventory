"""2026-09-23  Void PO-0174 and PO-0161 — batteries, no record wanted.

Scott: "po 174 and 161 are consumables not inventoried" then "just void the
po's we dont need a record of batteries at this point."

PO-0174 is a 12-pack of D cells (part 1213), PO-0161 a 36-pack of AAA (1176).
Both still Placed with received=0, so both were aging in the open-PO list.

Rejected receiving them. That would have made stock rows of 12 and 36 loose
cells that nobody will ever decrement, and the count would drift from the drawer
in a week. A count nobody maintains is how a stock system starts lying.

Rejected closing them Complete with the lines marked received. That was the
plan until Scott's second message: it keeps the price history, but an order
reading Complete with received=1 and no stock row anywhere is exactly what a
missed receive looks like, and it would have needed three separate notes to
defend. Cancelled needs none - it is the status that already means "this order
is not going to produce stock, stop watching it."

Nothing is deleted. Parts 1213 and 1176 stay active at 0 stock; the cancelled
orders keep the vendor, date and price if anyone ever asks what D cells cost.
Neither part is deactivated, because on this install active=False with 0 stock
is a MERGE RECEIPT and would claim these were merged into something else.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()

from order.models import PurchaseOrder
from order.status_codes import PurchaseOrderStatus
from stock.models import StockItem

COMMIT = "--commit" in sys.argv
TARGETS = ["PO-0174", "PO-0161"]
CANCELLED = PurchaseOrderStatus.CANCELLED.value

for ref in TARGETS:
    po = PurchaseOrder.objects.get(reference=ref)
    print("=== %s  %s  %s" % (ref, po.get_status_display(), (po.description or "")[:58]))
    for li in po.lines.all():
        p = li.part.part
        rows = StockItem.objects.filter(part=p).count()
        print("   line %s -> part %s %s" % (li.pk, p.pk, p.name[:46]))
        print("      qty=%g received=%g  price=%s   stock rows for this part: %d"
              % (li.quantity, li.received, li.purchase_price, rows))
        assert li.received == 0, "%s line %s already received - stop and look" % (ref, li.pk)
        assert rows == 0, "part %s already has stock - voiding would orphan it" % p.pk

    if not COMMIT:
        print("   DRY RUN: would set status -> Cancelled\n")
        continue

    PurchaseOrder.objects.filter(pk=po.pk).update(status=CANCELLED)
    po.refresh_from_db()
    ok = po.status == CANCELLED
    print("   %s -> %s   %s\n" % (ref, po.get_status_display(), "OK" if ok else "FAILED"))

if COMMIT:
    print("READBACK")
    bad = 0
    for ref in TARGETS:
        po = PurchaseOrder.objects.get(reference=ref)
        rows = sum(StockItem.objects.filter(part=li.part.part).count() for li in po.lines.all())
        good = po.status == CANCELLED and rows == 0
        bad += 0 if good else 1
        print("  %-9s %-10s  stock rows created: %d  %s"
              % (ref, po.get_status_display(), rows, "OK" if good else "FAILED"))
    openpos = PurchaseOrder.objects.filter(status=PurchaseOrderStatus.PLACED.value).count()
    print("\n  orders still Placed across the whole install: %d" % openpos)
    print("\n%s  both battery orders voided, no stock created"
          % ("[OK] SUCCESS" if not bad else "[X] FAILED"))
