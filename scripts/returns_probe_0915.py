#!/usr/bin/env python3
"""Read-only probe, 2026-09-15 daytime sweep.

Two questions, neither decidable from the task file:
  1. Which PO (if any) carries Amazon order 113-2048573-8975434, the Monoprice
     DP->HDMI MST hub that was returned and refunded 2026-09-15?
  2. Does the decision queue ALREADY carry an item about returned/refunded
     orders, so this run does not queue a duplicate?

Writes nothing.
"""
import os
import re
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django  # noqa: E402

django.setup()

from order.models import PurchaseOrder  # noqa: E402

REFS = ["113-2048573-8975434", "113-0519734-2405002"]

print("=== POs for returned orders ===")
for ref in REFS:
    qs = PurchaseOrder.objects.filter(supplier_reference=ref)
    if not qs.exists():
        print(f"  {ref}: no PO (never imported)")
        continue
    for po in qs:
        lines = po.lines.all()
        print(f"  {ref}: {po.reference} status={po.get_status_display()} "
              f"supplier={po.supplier.name} lines={lines.count()}")
        for ln in lines:
            sp = ln.part
            print(f"      part #{sp.part.pk} {sp.part.name!r} qty={ln.quantity} "
                  f"price={ln.purchase_price}")
        # has any stock been received against it?
        print(f"      received lines: "
              f"{sum(1 for ln in lines if ln.received and ln.received > 0)}")

print()
print("=== decision queue: any existing item about returns/refunds? ===")
QUEUE = "/Volumes/4TB_Removable/inventree/pending_decisions.md"
if not os.path.exists(QUEUE):
    print(f"  QUEUE NOT FOUND at {QUEUE} -- cannot check for duplicates")
    sys.exit(0)

with open(QUEUE, encoding="utf-8") as fh:
    lines = fh.readlines()

pat = re.compile(r"return|refund|rma|cancel", re.I)
hits = 0
for i, ln in enumerate(lines, 1):
    if not ln.lstrip().startswith("- ["):
        continue
    if pat.search(ln):
        hits += 1
        open_box = ln.lstrip().startswith("- [ ]")
        slug = ln.split("|")[0].strip().lstrip("- [x]").lstrip("- [ ]").strip()
        print(f"  line {i} open={open_box} slug={slug[:70]!r}")
        # show just the matching words in context
        for m in pat.finditer(ln):
            s = max(0, m.start() - 60)
            print(f"        ...{ln[s:m.end()+60].strip()}...")
        print()
print(f"  total checkbox lines matching return/refund/rma/cancel: {hits}")

total_open = sum(1 for ln in lines if ln.lstrip().startswith("- [ ]"))
print(f"  total OPEN items in queue: {total_open}")
