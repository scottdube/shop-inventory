"""Audit: PO lines that report received > 0 but whose part holds no stock.

Raised by the open decision `po0134-received-but-no-stock` (2026-08-25), which
found PO-0134 Complete with received=1.0 and part #1057 holding ZERO StockItem
rows, and asked whether other Complete POs have the same gap. This answers that
question instead of re-deriving it by hand each time.

A hit is NOT automatically a bug. Three benign explanations exist and the script
cannot tell them apart, so it prints the evidence and judges nothing:
  * the stock was received and then fully consumed or scrapped;
  * the item was returned after receipt (PO-0134's actual story);
  * the part is a consumable tracked only by purchase, never stocked.
The one it is looking for is the fourth: a .save() that reported success and
wrote nothing -- this install has that trap documented in docs/TRAPS.md.

Read-only.

Usage:  itq run scripts/received_no_stock.py
        itq run scripts/received_no_stock.py --since 2026-08-01
"""

import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrderLineItem  # noqa: E402
from stock.models import StockItem  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--since", default=None, help="only POs issued on/after YYYY-MM-DD")
a = ap.parse_args()

qs = PurchaseOrderLineItem.objects.filter(received__gt=0).select_related(
    "order", "part", "part__part"
)
if a.since:
    qs = qs.filter(order__issue_date__gte=a.since)

hits = 0
checked = 0
for ln in qs.order_by("order__reference", "pk"):
    if not ln.part or not ln.part.part:
        continue
    checked += 1
    part = ln.part.part
    items = StockItem.objects.filter(part=part)
    if items.exists():
        continue
    hits += 1
    po = ln.order
    print(f"{po.reference}  {po.get_status_display()}  supplier_ref={po.supplier_reference!r}")
    print(f"  line {ln.pk}: received={ln.received} of qty={ln.quantity}  SKU={ln.part.SKU}")
    print(f"  part #{part.pk} {part.full_name}  -> 0 StockItem rows")
    print(f"  {po.issue_date} issued / {po.complete_date} completed")
    print()

print(f"checked {checked} received line(s); {hits} with zero stock")
