#!/usr/bin/env python3
"""Overnight 2026-10-26 probe: queue A open-PO pool + queue D empty keywords.

Read-only. Same shape as probe_1024_0205.py, recent window moved to pk >= 1454
so the 10-25 daytime inflow (PO-0271, eBay Mitutoyo 293-349 micrometer #1457)
shows with its image and keyword state.
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
              f"link={p.link or '-'} splink={sp.link or '-'} "
              f"kw={'Y' if p.keywords else 'N'} name={p.name[:70]!r}")

hwm = Part.objects.order_by("-pk").first()
print(f"part HWM: {hwm.pk} {hwm.name[:60]!r}")
for p in Part.objects.filter(pk__gte=1454).order_by("pk"):
    print(f"recent {p.pk} img={'Y' if p.image else 'N'} kw={p.keywords or '-'!r} "
          f"active={p.active} link={p.link or '-'} {p.name[:60]!r}")

act = Part.objects.filter(active=True)
empty_kw = act.filter(keywords__isnull=True) | act.filter(keywords="")
print(f"active empty-keywords: {empty_kw.count()}")
for p in empty_kw.order_by("pk")[:30]:
    print(f"  KW {p.pk} cat={p.category.pathstring if p.category else '-'} "
          f"desc={(p.description or '')[:80]!r} name={p.name[:60]!r}")
have = act.exclude(image="").exclude(image__isnull=True).count()
print(f"coverage: {have}/{act.count()} active parts have an image")
newest = PurchaseOrder.objects.order_by("-pk").first()
print(f"newest PO: {newest.reference} sref={newest.supplier_reference} status={newest.status}")
