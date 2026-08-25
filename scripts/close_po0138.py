"""Close PO-0138 — fully received, still PLACED, so it keeps aging.

Same shape as close_po0020.py. An order with 0 lines outstanding that stays
PLACED sits in the open-PO list forever and every aging rule keeps counting it.

    itq run scripts/close_po0138.py            # dry run
    itq run scripts/close_po0138.py --commit
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder              # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

po = PurchaseOrder.objects.get(reference="PO-0138")
outstanding = [l for l in po.lines.all() if l.received < l.quantity]
print(f"PO-0138 status={po.get_status_display()} issued={po.issue_date} "
      f"outstanding_lines={len(outstanding)}")
if outstanding:
    sys.exit("!! lines still outstanding — not closing")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

PurchaseOrder.objects.filter(pk=po.pk).update(status=PurchaseOrderStatus.COMPLETE.value)
got = PurchaseOrder.objects.get(pk=po.pk)
assert got.status == PurchaseOrderStatus.COMPLETE.value, f"did not stick: {got.status}"
print(f"OK  PO-0138 -> {got.get_status_display()}")
