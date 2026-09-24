"""Overnight 2026-09-24: measure the three inflow pools in one connection.

1. Imageless parts on OPEN purchase orders (queue A priority).
2. LIVE parts with empty keywords (queue D top-up; NULL-aware, see TRAPS).
3. Imageless parts created since the last run's measure (queue A inflow),
   with every handle they carry: IPN, link, supplier SKU and link.

Read-only.
"""
import datetime
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from order.status_codes import PurchaseOrderStatusGroups  # noqa: E402
from part.models import Part  # noqa: E402

NOIMG = Q(image="") | Q(image__isnull=True)
EMPTY_KW = Q(keywords="") | Q(keywords__isnull=True)

print("=== 1. open POs, imageless parts ===")
open_pos = PurchaseOrder.objects.filter(status__in=PurchaseOrderStatusGroups.OPEN).order_by("pk")
print(f"open POs: {open_pos.count()}")
seen = set()
for po in open_pos:
    for li in po.lines.select_related("part__part", "part__supplier"):
        sp = li.part
        if not sp or not sp.part or sp.part.pk in seen:
            continue
        p = sp.part
        seen.add(p.pk)
        if p.image:
            continue
        print(f"  {po.reference:<8} {po.supplier.name if po.supplier else '?':<18} part={p.pk:<5} "
              f"SKU={sp.SKU!r} link={(sp.link or p.link or '')!r} | {p.name[:70]}")
print(f"parts on open POs: {len(seen)}")

print("\n=== 2. LIVE empty keywords ===")
for p in Part.objects.filter(EMPTY_KW, active=True).order_by("pk"):
    print(f"  part={p.pk} cat={p.category.pathstring if p.category else '-'} | {p.name} | {(p.description or '')[:120]}")
print(f"empty total={Part.objects.filter(EMPTY_KW).count()} live={Part.objects.filter(EMPTY_KW, active=True).count()}"
      f" of {Part.objects.count()}")

print("\n=== 3. imageless parts, newest 25 by pk ===")
noimg = Part.objects.filter(NOIMG, active=True)
print(f"imageless active={noimg.count()}  all imageless={Part.objects.filter(NOIMG).count()}  "
      f"parts total={Part.objects.count()}")
for p in noimg.order_by("-pk")[:25]:
    sps = SupplierPart.objects.filter(part=p).select_related("supplier")
    handles = "; ".join(f"{s.supplier.name}:{s.SKU} {s.link or ''}".strip() for s in sps) or "no-SP"
    print(f"  part={p.pk:<5} IPN={p.IPN!r} link={p.link!r} [{handles}] | {p.name[:70]}")

print(f"\nmax part pk: {Part.objects.order_by('-pk').first().pk}  now={datetime.datetime.now():%Y-%m-%d %H:%M}")
