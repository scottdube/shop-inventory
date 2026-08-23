"""Look up POs by vendor order number (supplier_reference) — the idempotency key.

InvenTree forces the visible `reference` to PO-nnnn, so the vendor's own order
number lives in `supplier_reference`. That field, not the reference, is what
tells you whether tonight's sweep has already imported an order. Checking the
wrong one is how the same order gets a second PO.

Read-only. Give it order numbers; it says which already exist.
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("orders", nargs="*")
ap.add_argument("--recent", type=int, default=0, help="also list N most recent POs")
a = ap.parse_args()

for o in a.orders:
    hits = PurchaseOrder.objects.filter(supplier_reference=o) | \
           PurchaseOrder.objects.filter(reference=o)
    hits = hits.distinct()
    if hits.exists():
        for po in hits:
            print(f"EXISTS  {o} -> {po.reference} (supplier_ref={po.supplier_reference!r}, "
                  f"status={po.get_status_display()}, supplier={po.supplier}, lines={po.lines.count()})")
    else:
        print(f"absent  {o}")

if a.recent:
    print(f"\n--- {a.recent} most recent POs ---")
    for po in PurchaseOrder.objects.order_by("-pk")[: a.recent]:
        n = po.lines.count()
        priced = po.lines.exclude(purchase_price=None).count()
        print(f"{po.reference:12s} supplier_ref={str(po.supplier_reference)[:28]:28s} "
              f"{po.get_status_display():10s} {str(po.supplier)[:18]:18s} "
              f"lines={n} priced={priced} date={po.issue_date}")
