#!/usr/bin/env python3
"""Book PO-0182 (DC barrel jacks, 20-pack, $7.99) for return to Amazon.

Scott, 2026-10-04: "182 is going to be returned".

Never received in InvenTree and part #1261 has no stock rows, so -- as with
PO-0165 -- there is no stock to quarantine. Rejected: receiving it first and
setting the row to 75 Quarantined. That is the path for goods already on the
books; here it would invent a row only to retire it.

Status 60 RETURNED now, though the box has not gone back yet: refund_watch.py
reads 60 as "a return is in play" and keeps the order on its list until the
[REFUND-CONFIRMED] sentinel lands, so the pending state is tracked, not lost.
complete_date stays None. No reason recorded -- Scott gave none.

    itq run scripts/return_po182_1004.py
    itq run scripts/return_po182_1004.py --commit
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem  # noqa: E402

COMMIT = "--commit" in sys.argv
RETURNED = 60

po = PurchaseOrder.objects.get(reference="PO-0182")
line = po.lines.get()
part = line.part.part
rows = StockItem.objects.filter(part=part).count()
print(f"{po.reference} status={po.status} -> {RETURNED}  {part.name}  ${po.total_price}")
print(f"  received {float(line.received):g} of {float(line.quantity):g}; stock rows for #{part.pk}: {rows}")
assert po.status == 20 and float(line.received) == 0 and rows == 0, "not the clean case"

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

note = (po.notes or "").rstrip() + (
    "\n\n**RETURN PENDING 2026-10-04.** Scott: \"182 is going to be returned\". "
    "Never received here, so there is no stock to reverse. Status 60 (RETURNED) "
    "set before the box goes back so refund_watch tracks it; complete_date left "
    "unset. Refund not yet confirmed. Reason not recorded -- none given.")
PurchaseOrder.objects.filter(pk=po.pk).update(status=RETURNED, notes=note)

pnote = (part.notes or "").rstrip()
if "NOT OWNED" not in pnote:
    Part.objects.filter(pk=part.pk).update(notes=pnote + (
        "\n\n**NOT OWNED — the one order for this part (PO-0182) is being RETURNED** "
        "(2026-10-04), never received. Zero stock means never held, not mislaid."))

po.refresh_from_db(); part.refresh_from_db()
print(f"  re-read: status {po.status}  complete_date {po.complete_date}  "
      f"pending-note {'RETURN PENDING' in po.notes}  part not-owned {'NOT OWNED' in part.notes}")
