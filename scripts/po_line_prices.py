"""Print line-item prices for one or more POs by supplier_reference or reference.

Read-only. Exists because the Amazon 'Grand Total' trap means a PO can be
created with null or wrong prices and nothing downstream notices until a
receive. Checking the freshest PO each sweep is one query.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder  # noqa: E402

for key in sys.argv[1:]:
    po = (
        PurchaseOrder.objects.filter(supplier_reference=key).first()
        or PurchaseOrder.objects.filter(reference=key).first()
    )
    if po is None:
        print(f"NOT FOUND  {key}")
        continue
    print(f"{po.reference}  supplier_ref={po.supplier_reference}  status={po.get_status_display()}")
    for line in po.lines.all():
        part = line.part.part.name if line.part else "(no part)"
        price = line.purchase_price
        flag = "  <-- NULL PRICE" if price is None else ""
        print(f"    qty={line.quantity:>6}  price={price}  {part[:70]}{flag}")
    print()
