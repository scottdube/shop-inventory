"""Dump a purchase order's lines: reference, supplier_reference, status, lines.

Read-only. Exists because po_check.py answers only "does this order number
already have a PO?" -- it reports a line COUNT, which cannot distinguish a
complete 1-line order from a 2-line order that lost a line to a silent save.
Seen 2026-08-25 on PO-0142 (Walmart 2-unit order, lines=1); the count was
right for the wrong reason (qty 2 on one line), and there was no cheap way to
tell without this.

Usage:  itq run scripts/po_show.py PO-0142 [PO-0141 ...]
        itq run scripts/po_show.py --supplier-ref 2000151-82176030
"""

import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder  # noqa: E402


def show(po):
    print(f"{po.reference}  supplier_ref={po.supplier_reference!r}  "
          f"status={po.get_status_display()}  supplier={po.supplier.name}")
    print(f"  issue_date={po.issue_date}  complete_date={po.complete_date}")
    if po.notes:
        print(f"  notes: {po.notes.strip()[:400]}")
    for ln in po.lines.all().order_by("pk"):
        part = ln.part.part.full_name if ln.part else "(no supplier part)"
        sku = ln.part.SKU if ln.part else "-"
        print(f"  line {ln.pk}: qty={ln.quantity} received={ln.received} "
              f"price={ln.purchase_price} SKU={sku}")
        print(f"    part: {part}")
        if ln.notes:
            print(f"    notes: {ln.notes.strip()[:300]}")
    print()


args = sys.argv[1:]
if not args:
    sys.exit(__doc__)

if args[0] == "--supplier-ref":
    qs = PurchaseOrder.objects.filter(supplier_reference__in=args[1:])
else:
    qs = PurchaseOrder.objects.filter(reference__in=args)

if not qs.exists():
    print("no match")
for po in qs:
    show(po)
