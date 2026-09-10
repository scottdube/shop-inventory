"""Decision-queue rule 3 audit, 2026-09-10. READ-ONLY.

The task file says lines marked `[x] APPROVED` are to be EXECUTED and then moved
to a `## done` section. Seven such lines are still sitting in the open body of
pending_decisions.md. Before doing anything, establish which of them were in fact
already carried out and merely never moved -- because "still in the list" and
"still undone" are different claims, and acting on the first as if it were the
second is how a PO gets created twice.

The idempotency key is supplier_reference (InvenTree forces PO-nnnn references),
so for every Amazon order number named in an APPROVED line, this reports whether
a PurchaseOrder already carries it, and in what state.
"""
import os
import re
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402

ROOT = "/Volumes/4TB_Removable/inventree"
PEND = os.path.join(ROOT, "pending_decisions.md")
ORDER_RE = re.compile(r"\b(\d{3}-\d{7}-\d{7})\b")

section = "open"
rows = []
with open(PEND) as fh:
    for ln in fh:
        s = ln.strip()
        if s.startswith("## "):
            section = s[3:].strip().lower()
            continue
        if s.startswith("- [x] APPROVED") or s.startswith("- [x]APPROVED"):
            rows.append((section, s))

print(f"APPROVED lines found: {len(rows)}")
for section, s in rows:
    m = ORDER_RE.search(s)
    ref = m.group(1) if m else None
    print()
    print(f"  section={section}")
    print(f"  {s[:150]}")
    if not ref:
        print("    -> no order number in the line; cannot key it, leaving alone")
        continue
    pos = list(PurchaseOrder.objects.filter(supplier_reference=ref))
    if pos:
        for po in pos:
            print(f"    -> ALREADY DONE: {po.reference} "
                  f"{PurchaseOrderStatus(po.status).label} "
                  f"({po.supplier.name if po.supplier else '?'}) "
                  f"lines={po.lines.count()}")
    else:
        print(f"    -> NO PO carries supplier_reference {ref} -- genuinely outstanding")

print()
print("-- section headings present in the file --")
with open(PEND) as fh:
    for ln in fh:
        if ln.strip().startswith("## "):
            print(f"   {ln.rstrip()}")
