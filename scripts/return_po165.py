#!/usr/bin/env python3
"""Mark PO-0165 returned to Amazon.

Scott, 2026-09-16: "returned to amazon", with PO-0165 ticked in the purchasing
table. NOT the monitor discussed in the preceding messages -- the checkbox was
on PO-0165 and that is what was read. The item is the Monoprice DisplayPort
1.2 to 2x DisplayPort MST hub, $44.99, ASIN B075754ZYC.

Clean return: nothing was ever received against this order and part #1185 has
no stock rows, so there is no stock to reverse and no cost already booked.

Status 60 (RETURNED), matching PO-0029 and PO-0155. complete_date is left
None, as on both of those -- a returned order was never completed, and
stamping a completion date would make it look fulfilled in any report that
keys on that field.

WHY it went back is NOT recorded, because Scott did not say. The sibling
PO-0163 -- DP 1.2 to 2x HDMI MST hub, #1181 -- is still open, so the obvious
inference is that the HDMI variant was the right one and this was the wrong
guess. That is a plausible story and nothing tested it, so it stays out of
the record.

    itq run scripts/return_po165.py
    itq run scripts/return_po165.py --commit
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

po = PurchaseOrder.objects.get(reference="PO-0165")
line = po.lines.first()
part = line.part.part

print(f"{po.reference}  status={po.status} -> {RETURNED} (RETURNED)")
print(f"  {part.name}  ${po.total_price}")
print(f"  received {float(line.received):g} of {float(line.quantity):g}")
print(f"  stock rows for #{part.pk}: {StockItem.objects.filter(part=part).count()}")

assert float(line.received) == 0, "stock was received — a return needs reversing first"

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

note = ((po.notes or "").rstrip() + "\n\n" if po.notes else "") + (
    "**RETURNED TO AMAZON 2026-09-16.** Scott: \"returned to amazon\".\n\n"
    "Nothing was received against this order and part #1185 has no stock rows, "
    "so there was no stock to reverse and no cost booked. Status set to 60 "
    "(RETURNED) with complete_date left unset — a returned order was never "
    "completed, and a completion date would make it read as fulfilled.\n\n"
    "REASON NOT RECORDED because Scott did not give one. The sibling order "
    "PO-0163 (DP 1.2 to 2x **HDMI** MST hub, #1181) is still open, which "
    "suggests the HDMI variant was the one actually wanted — but that is an "
    "inference and it is deliberately not written as the reason.")
PurchaseOrder.objects.filter(pk=po.pk).update(status=RETURNED, notes=note)
po.refresh_from_db()
print(f"\n  status now {po.status}  complete_date {po.complete_date}")

pnote = (part.notes or "").rstrip()
add = ("\n\n**NOT OWNED — the one order for this part was RETURNED.** PO-0165 "
       "($44.99, ASIN B075754ZYC) went back to Amazon 2026-09-16 without being "
       "received. The part record is kept because it documents a considered "
       "purchase and the ASIN stays resolvable, but zero stock here means never "
       "held, not mislaid — do not go looking for it.\n\n"
       "The DisplayPort-to-2x-**HDMI** sibling is #1181, on the still-open "
       "PO-0163.")
if "NOT OWNED" not in pnote:
    Part.objects.filter(pk=part.pk).update(notes=pnote + add)
    part.refresh_from_db()
print(f"  part #{part.pk} marked not-owned: {'NOT OWNED' in part.notes}")
