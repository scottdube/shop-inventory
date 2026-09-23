"""Queue A, 2026-09-23: imageless parts sitting on OPEN purchase orders.

Section A says parts on open (Placed) POs jump the queue, so the picture is on
the part before the box lands. Measure that pool first, every run: it refills as
queue C raises POs, which is why it is never "closed" the way the aged-out ASIN
pool is.

Read-only.
"""
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder  # noqa: E402
from order.status_codes import PurchaseOrderStatusGroups  # noqa: E402

open_pos = PurchaseOrder.objects.filter(status__in=PurchaseOrderStatusGroups.OPEN).order_by("pk")
print(f"open POs: {open_pos.count()}")
seen = set()
for po in open_pos:
    for li in po.lines.select_related("part__part", "part__supplier"):
        sp = li.part
        if not sp or not sp.part:
            continue
        p = sp.part
        if p.pk in seen:
            continue
        seen.add(p.pk)
        has = bool(p.image)
        print(f"{po.reference:<8} {po.supplier.name if po.supplier else '?':<22} "
              f"{'IMG ' if has else 'none'} part={p.pk:<5} SKU={sp.SKU!r:<22} "
              f"link={(sp.link or p.link or '')[:60]!r} | {p.name[:60]}")
print(f"\nparts on open POs: {len(seen)}")
