"""Queue B probe 2 — every Tormach and MSC PO on the instance, by supplier.

Probe 1 found all three orders the task file lists as un-imported already in as
PO-0025/0026/0027, so the task file's queue-B remainder list is stale. This
prints the actual state: which vendor order numbers ARE in, so the gap can be
computed against the Gmail list instead of against the file's memory of it.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402

for pk in (7, 8):
    c = Company.objects.get(pk=pk)
    pos = PurchaseOrder.objects.filter(supplier=c).order_by("pk")
    print(f"\n=== {c.name} — {pos.count()} POs ===")
    for po in pos:
        n = po.lines.count()
        priced = po.lines.exclude(purchase_price=None).count()
        print(f"{po.reference:9s} supplier_ref={str(po.supplier_reference):14s} "
              f"{po.get_status_display():9s} lines={n} priced={priced} "
              f"issue={po.issue_date} created={po.creation_date}")
        for line in po.lines.all().order_by("pk"):
            sku = line.part.SKU if line.part else "-"
            print(f"    {sku:12s} qty={line.quantity:>8} "
                  f"price={line.purchase_price} recv={line.received} "
                  f"part=#{line.part.part.pk if line.part else '?'}")
