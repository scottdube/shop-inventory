"""Read-only: print the /web/ URLs for what the 16:40 2026-09-18 sweep touched.

A bare pk is unlookupable from a chat reply, so the report cites links.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder  # noqa: E402
from part.models import Part  # noqa: E402

BASE = "http://inventory.internal:8001"

for ref in ("PO-0175", "PO-0174"):
    po = PurchaseOrder.objects.get(reference=ref)
    print(f"{ref}  {BASE}/web/purchasing/purchase-order/{po.pk}"
          f"   status={po.get_status_display()}  ref={po.supplier_reference}")

p = Part.objects.get(pk=1214)
print(f"part  {BASE}/web/part/{p.pk}   {p.name}")
