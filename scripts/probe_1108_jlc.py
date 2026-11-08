#!/usr/bin/env python3
"""Overnight 2026-11-08: which JLCPCB orders are already POs, and the open PO list.

Read-only. A JLCPCB 'Your Order Is On Its Way' mail arrived 2026-11-07 08:56;
the registry says jlcpcb.com is known-NOT-swept (parts entered by hand), so
this only checks whether the shipped order is already recorded somewhere.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402

for c in Company.objects.filter(name__icontains="jlc"):
    print(f"company #{c.pk} {c.name} supplier={c.is_supplier}")
    for po in PurchaseOrder.objects.filter(supplier=c).order_by("-pk"):
        lines = "; ".join(f"{ln.quantity:g}x {ln.part.part.name[:40] if ln.part else '?'}"
                          for ln in po.lines.all())
        print(f"  {po.reference} sref={po.supplier_reference} status={po.status} "
              f"created={po.creation_date} issued={po.issue_date} lines=[{lines}]")

print("\nplaced POs:")
for po in PurchaseOrder.objects.filter(status=PurchaseOrderStatus.PLACED.value).order_by("-pk"):
    print(f"  {po.reference} sref={po.supplier_reference} "
          f"supplier={po.supplier.name if po.supplier else '-'} created={po.creation_date}")
