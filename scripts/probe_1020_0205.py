#!/usr/bin/env python3
"""Overnight 2026-10-20 probe: queue A open-PO pool + queue D empty keywords.

Read-only. Lists every part on a PLACED purchase order that has no image,
with its supplier SKUs and link, plus the high-water mark of part pks and the
count of active parts with empty keywords. Same shape as probe_1019_0205.py,
recent window moved to pk >= 1416 (last night's HWM).
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402
from part.models import Part  # noqa: E402

placed = PurchaseOrder.objects.filter(status=PurchaseOrderStatus.PLACED.value)
print(f"placed POs: {placed.count()}")
seen = set()
for po in placed.order_by("-pk")[:40]:
    for line in po.lines.all():
        sp = line.part
        if not sp or sp.part_id in seen:
            continue
        p = sp.part
        seen.add(p.pk)
        if p.image:
            continue
        print(f"NOIMG {po.reference} sref={po.supplier_reference} part={p.pk} "
              f"sku={sp.SKU} supplier={sp.supplier.name} active={p.active} "
              f"link={p.link or '-'} name={p.name[:70]!r}")

hwm = Part.objects.order_by("-pk").first()
print(f"part HWM: {hwm.pk} {hwm.name[:60]!r}")
for p in Part.objects.filter(pk__gte=1416).order_by("pk"):
    print(f"recent {p.pk} img={'Y' if p.image else 'N'} kw={'Y' if p.keywords else 'N'} {p.name[:60]!r}")

act = Part.objects.filter(active=True)
empty_kw = act.filter(keywords__isnull=True).count() + act.filter(keywords="").count()
have = act.exclude(image="").exclude(image__isnull=True).count()
print(f"active empty-keywords: {empty_kw}")
print(f"coverage: {have}/{act.count()} active parts have an image")
