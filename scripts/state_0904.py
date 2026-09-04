"""State read for the 2026-09-04 02:05 overnight run. Read-only.

Queues A, B and D were all closed with evidence (decisions queue-a-exhausted,
queue-b-section-stale, queue-d-closed-file-says-ongoing). A closure is a
statement about a SET, not a promise about parts created later — so the only
thing worth re-walking each night is the delta: parts created since the last
run, and imageless parts sitting on POs that are actually open.

Takes the PO status codes from the enum, and prints the whole histogram beside
the count. That is the 2026-09-03 measurement bug: order__status=10 is PENDING,
not PLACED, and the wrong query printed "open POs: 0" while hiding the single
part that was that night's only work.
"""
import os
import sys
from collections import Counter
from datetime import timedelta

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.utils import timezone  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402
from part.models import Part  # noqa: E402

active = Part.objects.filter(active=True)
print(f"active parts            : {active.count()}")
print(f"  imageless (active)    : {active.filter(image='').count()}")
print(f"  empty keywords        : {active.filter(keywords='').count()}")
print(f"  empty keywords (all)  : {Part.objects.filter(keywords='').count()}")

print()
print("-- PO status histogram (codes from the enum, not literals) --")
hist = Counter(PurchaseOrder.objects.values_list("status", flat=True))
labels = {int(v): v.label for v in PurchaseOrderStatus.values()} if False else {}
for code, n in sorted(hist.items()):
    try:
        label = PurchaseOrderStatus(code).label
    except ValueError:
        label = "?"
    print(f"   {code:3d} {label:<12} {n}")

OPEN = [PurchaseOrderStatus.PENDING.value, PurchaseOrderStatus.PLACED.value]
print(f"   OPEN codes = {OPEN}")

print()
print("-- imageless parts on OPEN purchase orders (queue A jumps these) --")
lines = (PurchaseOrderLineItem.objects
         .filter(order__status__in=OPEN)
         .select_related("order", "part", "part__part", "order__supplier"))
seen = set()
for li in lines:
    sp = li.part
    p = sp.part if sp else None
    if not p or p.pk in seen:
        continue
    seen.add(p.pk)
    if p.image:
        continue
    print(f"   pk {p.pk:5d} | {p.name[:52]:<52} | "
          f"{li.order.reference} {PurchaseOrderStatus(li.order.status).label:<8} | "
          f"{(li.order.supplier.name if li.order.supplier else '?')}:{sp.SKU}")
if not seen:
    print("   (no lines on open POs at all)")

print()
print("-- parts created in the last 3 days (what the closures cannot cover) --")
since = timezone.now() - timedelta(days=3)
for p in Part.objects.filter(creation_date__gte=since.date()).order_by("pk"):
    print(f"   pk {p.pk:5d} | {p.name[:46]:<46} | created {p.creation_date} | "
          f"img={'Y' if p.image else 'n'} kw={'Y' if p.keywords else 'n'} "
          f"link={'Y' if p.link else 'n'} active={p.active}")

print()
print("-- most recent POs (for the queue C sweep window) --")
for po in PurchaseOrder.objects.order_by("-pk")[:12]:
    print(f"   {po.reference:<9} {PurchaseOrderStatus(po.status).label:<10} "
          f"{str(po.issue_date or po.creation_date):<12} "
          f"{(po.supplier.name if po.supplier else '?'):<22} "
          f"supplier_ref={po.supplier_reference!r}")
