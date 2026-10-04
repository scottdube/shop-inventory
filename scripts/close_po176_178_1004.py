"""Close PO-0176 (seller cancelled) and PO-0178 (a toy, not inventory), 2026-10-04.

Scott: "176 was CX by seller, 178 is a non inventory toy".

PO-0176 -> CANCELLED (40). Nothing shipped, so a cancelled order is the truth.
  Part #1215 (T400 4GB LP) was the sole item and has no other order or stock:
  deactivated with a NOT INVENTORY marker so every filter that already skips
  that tag skips it. The PNY T400 2GB on PO-0187 is the card that did arrive.

PO-0178 -> COMPLETE (30), line marked received, NO stock row. Rejected:
  cancelling it. The kit arrived and $39.10 left -- a cancelled order says
  neither happened (TRAPS, the returns write-up). It is simply not shop stock.
  Part #1238 deactivated the same way, kept rather than deleted so the PO line
  keeps its part.

All writes by queryset .update(), then re-read.

    itq run scripts/close_po176_178_1004.py            # dry run
    itq run scripts/close_po176_178_1004.py --commit
"""
import argparse
import datetime
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()
today = datetime.date(2026, 10, 4)

PLAN = [
    ("PO-0176", 40, False, 1215,
     "CANCELLED BY SELLER (sole item on order, never shipped) — NOT INVENTORY.",
     "CANCELLED 2026-10-04: Scott says the seller cancelled. Nothing received."),
    ("PO-0178", 30, True, 1238,
     "NOT INVENTORY — a toy, bought and received but not shop stock.",
     "COMPLETED 2026-10-04 with NO stock row: Scott says it is a non-inventory toy. "
     "Received and paid for, so not cancelled -- just not tracked."),
]

for ref, status, mark_recv, part_pk, part_tag, po_note in PLAN:
    po = PurchaseOrder.objects.get(reference=ref)
    lines = list(po.lines.all())
    part = Part.objects.get(pk=part_pk)
    assert len(lines) == 1 and lines[0].part.part_id == part_pk, ref
    assert po.status == 20, f"{ref} is status {po.status}, expected PLACED"
    stock = StockItem.objects.filter(part=part).count()
    other = PurchaseOrderLineItem.objects.filter(part__part=part).exclude(order=po).count()
    print(f"{ref}: status 20 -> {status}; line received -> {'qty' if mark_recv else 'unchanged'}; "
          f"part #{part_pk} {part.name[:45]!r} active -> False  (stock rows {stock}, other PO lines {other})")
    if stock or other:
        sys.exit(f"!! part #{part_pk} has stock or other orders -- not deactivating blind")
    if not args.commit:
        continue

    if mark_recv:
        PurchaseOrderLineItem.objects.filter(pk=lines[0].pk).update(received=lines[0].quantity)
    upd = dict(status=status, notes=((po.notes or "") + "\n\n" + po_note))
    if status == 30:
        upd["complete_date"] = today
    PurchaseOrder.objects.filter(pk=po.pk).update(**upd)
    desc = part.description or ""
    if "NOT INVENTORY" not in desc:
        desc = f"{part_tag} {desc}"[:250]
    Part.objects.filter(pk=part_pk).update(active=False, description=desc)

    po.refresh_from_db(); part.refresh_from_db(); ln = po.lines.get()
    print(f"   re-read: {ref} status={po.status} complete={po.complete_date} "
          f"recv={float(ln.received)}/{float(ln.quantity)} | part active={part.active} "
          f"desc={part.description[:60]!r}")

if not args.commit:
    print("\nDRY RUN -- add --commit")
