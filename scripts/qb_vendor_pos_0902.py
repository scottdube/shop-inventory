"""Every Tormach and MSC purchase order, with line and pricing coverage.

Closing queue B honestly means showing that each order email found in Gmail has
a PO, and that each PO's lines carry a price. A count of POs alone would not do
that -- an order imported with null prices is the exact failure queue B exists
to catch, and it looks identical to a success from the outside.

Read-only.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402

for name in ["Tormach", "MSC Industrial Supply"]:
    c = Company.objects.filter(name=name).first()
    if not c:
        print(f"{name}: NO SUCH SUPPLIER")
        continue
    pos = PurchaseOrder.objects.filter(supplier=c).order_by("issue_date", "pk")
    print(f"\n=== {name}: {pos.count()} purchase orders ===")
    for po in pos:
        lines = list(po.lines.all())
        priced = [l for l in lines if l.purchase_price is not None]
        flag = "" if len(priced) == len(lines) and lines else "   <-- UNPRICED LINES"
        print(f"  {po.reference:9s} supplier_ref={str(po.supplier_reference)[:14]:14s} "
              f"{po.get_status_display():9s} issue={po.issue_date} "
              f"lines={len(lines)} priced={len(priced)}{flag}")
