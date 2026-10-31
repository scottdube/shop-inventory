#!/usr/bin/env python3
"""Book PO-0259 (storm door push-button latch set, to The Villages FL) for return.

Scott, 2026-10-31: "259 to be returned". Same path as PO-0182: never received,
part #1408 has no stock rows, so status 60 RETURNED with complete_date None.
refund_watch.py reads 60 as "a return is in play" and keeps it listed until the
[REFUND-CONFIRMED] sentinel lands. No reason recorded -- Scott gave none.
The identical latch on PO-0258 was kept (received at SLN, not inventoried).

    itq run scripts/return_po259_1031.py [--commit]
"""
import os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from order.models import PurchaseOrder
from stock.models import StockItem
from plugins.notes_compat import note_append

COMMIT = "--commit" in sys.argv
po = PurchaseOrder.objects.get(reference="PO-0259")
line = po.lines.get()
rows = StockItem.objects.filter(part=line.part.part).count()
print(f"{po.reference} status={po.status} -> 60  {line.part.part.name[:50]}  rows={rows} received={float(line.received):g}")
if not COMMIT:
    print("DRY RUN"); sys.exit(0)
assert rows == 0 and float(line.received) == 0
PurchaseOrder.objects.filter(pk=po.pk).update(status=60)
po.refresh_from_db(); assert po.status == 60
note_append(po, "2026-10-31: status RETURNED (pending). Scott: \"259 to be returned\". Refund not yet seen.")
print("ok")
