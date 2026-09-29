"""Overnight 2026-09-29 02:05 state probe for queues A and D. Read-only.

Answers three questions before any work is chosen:
  1. inflow: parts created after #1264 (the last part the queues saw)
  2. queue D: ACTIVE parts with empty keywords
  3. queue A: imageless parts on open (Placed/Pending) purchase orders
"""
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from order.status_codes import PurchaseOrderStatusGroups  # noqa: E402
from part.models import Part  # noqa: E402

print(f"parts total={Part.objects.count()} max_pk={Part.objects.order_by('-pk').first().pk}")

new = Part.objects.filter(pk__gt=1264).order_by("pk")
print(f"\n1. inflow since #1264: {new.count()}")
for p in new:
    print(f"  #{p.pk} active={p.active} img={'Y' if p.image else '-'} "
          f"kw={'Y' if p.keywords else '-'} {p.name}")

empty_kw = Part.objects.filter(active=True).filter(Q(keywords__isnull=True) | Q(keywords=""))
print(f"\n2. queue D active empty-keyword rows: {empty_kw.count()}")
for p in empty_kw[:20]:
    print(f"  #{p.pk} {p.name}")

open_pos = PurchaseOrder.objects.filter(status__in=PurchaseOrderStatusGroups.OPEN)
lines = PurchaseOrderLineItem.objects.filter(order__in=open_pos).select_related("part__part")
seen = set()
print(f"\n3. open POs={open_pos.count()}; imageless parts on them:")
for li in lines:
    if not li.part:
        continue
    p = li.part.part
    if p.pk in seen or p.image:
        continue
    seen.add(p.pk)
    print(f"  #{p.pk} {li.order.reference} SKU={li.part.SKU} {p.name}")
print(f"  count={len(seen)}")

total = Part.objects.count()
with_img = Part.objects.exclude(Q(image__isnull=True) | Q(image="")).count()
print(f"\ncoverage {with_img}/{total}")
