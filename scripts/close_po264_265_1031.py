#!/usr/bin/env python3
"""Close PO-0264 (one line kept, one returned) and PO-0265 (returned).

Scott, 2026-10-31: "265 returned, 264 on bench no home, commuter".

The refunds were already MEASURED (refund_seen_0264_0265_1028.py): PO-0265's
Lark M2 2TX+3RX kit and PO-0264's PowerDeWise wireless kit (line 391) were
dropped off 10-23 and refunded. PO-0264's second line, the wired 3.5 mm
lavalier (#1415, line 392), was in no return mail -- that is what is on the
LRD bench.

  PO-0265 -> status 60 RETURNED. Never received, no stock rows, so nothing to
           quarantine (the PO-0182 path).
  PO-0264 -> line 392 received to LRD/Receiving (1 pc), line 391 left at 0
           received with a PO note saying it was returned and refunded, order
           CLOSED 30. Rejected 60 for 0264: it would say the wired lav went
           back too, and the wired lav is the one thing from that order still
           here. The commute mark is trip.py's job, run after this.

    itq run scripts/close_po264_265_1031.py
    itq run scripts/close_po264_265_1031.py --commit
"""
import datetime
import os
import sys
from decimal import Decimal

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402
from plugins.notes_compat import note_text, note_set, note_append  # noqa: E402

COMMIT = "--commit" in sys.argv
WHEN = datetime.date(2026, 10, 31)
dest = StockLocation.objects.get(pk=473)  # LRD/Receiving

p265 = PurchaseOrder.objects.get(reference="PO-0265")
p264 = PurchaseOrder.objects.get(reference="PO-0264")
kept = p264.lines.get(pk=392)
gone = p264.lines.get(pk=391)
assert "wired" in kept.part.part.name.lower(), kept.part.part.name
assert float(kept.part.pack_quantity_native or 1) == 1

rows265 = StockItem.objects.filter(part=p265.lines.get().part.part).count()
print(f"PO-0265 status {p265.status} -> 60 RETURNED; stock rows for its part: {rows265}")
print(f"PO-0264 line 392 {kept.part.part.name[:50]} -> 1 @ {dest.pathstring}, "
      f"${kept.purchase_price.amount}")
print(f"PO-0264 line 391 {gone.part.part.name[:50]} -> stays 0 received, noted returned")
print(f"PO-0264 status {p264.status} -> 30")
if not COMMIT:
    print("\nDRY RUN"); sys.exit(0)

assert rows265 == 0
p265.status = 60
p265.save(); p265.refresh_from_db()
if p265.status != 60:
    PurchaseOrder.objects.filter(pk=p265.pk).update(status=60); p265.refresh_from_db()
assert p265.status == 60
note_append(p265, f"{WHEN}: status RETURNED. Scott: \"265 returned\". Refund measured 10-28.")

assert not StockItem.objects.filter(part=kept.part.part, location=dest).exists()
unit = Decimal(str(kept.purchase_price.amount))
row = StockItem.objects.create(
    part=kept.part.part, location=dest, quantity=1, supplier_part=kept.part,
    purchase_order=p264, purchase_price=unit, purchase_price_currency="USD")
note_set(row, f"RECEIVED 1 on {WHEN} from PO-0264 at ${unit:.4f}. On the LRD bench, no home yet; commutes.")
row.refresh_from_db(); assert float(row.quantity) == 1
kept.received = kept.quantity
kept.save(); kept.refresh_from_db(); assert float(kept.received) == 1

note_append(p264, (f"{WHEN}: CLOSED with line 391 (PowerDeWise wireless kit) at 0 received -- "
                   f"it was returned (dropoff 10-23, refund $26.65 measured 10-28), never booked. "
                   f"Line 392 (wired lav) kept: on the LRD bench, a commuter."))
p264.status = 30; p264.complete_date = WHEN
p264.save(); p264.refresh_from_db()
if p264.status != 30:
    PurchaseOrder.objects.filter(pk=p264.pk).update(status=30, complete_date=WHEN); p264.refresh_from_db()
assert p264.status == 30
print(f"\nPO-0265 -> {p265.status}; PO-0264 -> {p264.status}; wired lav stock {row.pk}")
