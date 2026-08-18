"""Execute the approved decision queue: 5 stub POs + 2 cancellations.

Idempotent by supplier_reference (the lesson from the first sweep). Titles from
Scott's order-history pages go in the PO description, which makes these five
BETTER than the sweep's blind stubs. Gift-card orders get no invented prices.
"""
import os, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from company.models import Company
from order.models import PurchaseOrder
try:
    from order.status_codes import PurchaseOrderStatus
except ImportError:
    from InvenTree.status_codes import PurchaseOrderStatus

amazon = Company.objects.get(name__iexact="Amazon")

CREATE = [
    ("ORDER-REDACTED", "uxcell Fiberglass Insulation Sleeve 6mm high-temp, 15m",
     "18.68", "ordered 2026-08-14, IN TRANSIT (ETA Aug 25 - Sep 3). Leave Placed until it arrives."),
    ("ORDER-REDACTED", "uxcell 7x10cm Single-Sided Copper Clad Laminate PCB, 10 pcs",
     "9.99", "delivered 2026-07-25. PCB milling material."),
    ("ORDER-REDACTED", "CBAZY 22AWG Silicone Hookup Wire Kit, 6 colors x 19.6ft",
     "15.32", "delivered 2026-07-24. Its 20AWG twin order ORDER-REDACTED was cancelled - never create that one."),
    ("ORDER-REDACTED", "Screen printing: NEWISHTOOL squeegee 2pc + 3yd 110-mesh silk screen",
     None, "delivered 2026-08-05. Paid with gift card balance - order page shows $0.00; item prices unknown, not invented."),
    ("ORDER-REDACTED", "Screen printing: HRLORKC rubber brayer rollers, 4in + 2.2in",
     None, "delivered 2026-08-01. Paid with gift card balance - $0.00 shown; prices not invented."),
]
CANCEL = [
    ("ORDER-REDACTED", "vacuum chamber - REFUNDED, return in transit"),
    ("ORDER-REDACTED", "end mill set - RETURN STARTED"),
]

def next_ref():
    n = 0
    for r in PurchaseOrder.objects.values_list("reference", flat=True):
        if r and r.startswith("PO-"):
            try: n = max(n, int(r.split("-")[1]))
            except ValueError: pass
    return n + 1

for ref, title, total, note in CREATE:
    if PurchaseOrder.objects.filter(supplier_reference=ref).exists():
        print(f"  exists  {ref}  (skipped)"); continue
    po = PurchaseOrder.objects.create(
        supplier=amazon, supplier_reference=ref,
        reference=f"PO-{next_ref():04d}",
        description=title[:250],
        notes=(f"Stub PO from Scott's approved decision queue, executed "
               f"interactively {date.today().isoformat()}. "
               + (f"Order total ${total}. " if total else "")
               + note + " Line items not itemisable from Amazon email; "
               "reconcile from the order page if cost detail is ever needed."))
    po.status = PurchaseOrderStatus.PLACED.value
    po.save()
    print(f"  created {po.reference}  {ref}  {title[:44]}")

print()
for ref, why in CANCEL:
    po = PurchaseOrder.objects.filter(supplier_reference=ref).first()
    if not po:
        print(f"  CANCEL TARGET NOT FOUND: {ref}"); continue
    if po.status == PurchaseOrderStatus.CANCELLED.value:
        print(f"  already cancelled {po.reference}"); continue
    po.status = PurchaseOrderStatus.CANCELLED.value
    po.notes = ((po.notes or "").rstrip() +
                f"\n\nCANCELLED {date.today().isoformat()} per Scott: {why}.")
    po.save()
    print(f"  cancelled {po.reference}  {ref}  ({why.split(' - ')[0]})")

print()
from collections import Counter
c = Counter(PurchaseOrder.objects.values_list("status", flat=True))
print("PO totals by status:", dict(c))
