"""List recent purchase orders so the sweep can see what is already imported.

Written 2026-09-20 22:40 sweep. Reading the PO list directly is cheaper and more
reliable than re-reading giant vendor order emails to recover order numbers --
supplier_reference is the idempotency key, so printing it for everything recent
answers "was this already swept?" in one call.
"""
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django  # noqa: E402

django.setup()

from order.models import PurchaseOrder  # noqa: E402

qs = PurchaseOrder.objects.all().order_by("-pk")[:25]
for po in qs:
    print(
        f"{po.reference:<10} supplier_ref={po.supplier_reference!r:<28} "
        f"supplier={po.supplier.name if po.supplier else None!r:<20} "
        f"status={po.status} created={po.creation_date} lines={po.lines.count()}"
    )
