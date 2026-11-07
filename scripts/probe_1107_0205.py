#!/usr/bin/env python3
"""Overnight 2026-11-07 probe: queue A open-PO pool + inflow, queue D empty keywords.

Read-only. Same shape as probe_1106_0205.py; the recent window moves to
pk >= 1509 so the 11-06 inflow (PO-0291 MTCELL 1x7 headers on existing #1183,
anything the 11-06 daytime sessions created) is checked for image and keywords.
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
for p in Part.objects.filter(pk__gte=1509).order_by("pk"):
    skus = ",".join(f"{sp.supplier.name}:{sp.SKU}" for sp in p.supplier_parts.all())
    print(f"recent {p.pk} img={'Y' if p.image else 'N'} kw={'Y' if p.keywords else 'N'} "
          f"active={p.active} link={p.link or '-'} sp=[{skus}] {p.name[:60]!r}")

act = Part.objects.filter(active=True)
empty_kw = act.filter(keywords__isnull=True) | act.filter(keywords="")
print(f"active empty-keywords: {empty_kw.count()}")
for p in empty_kw.order_by("pk")[:30]:
    print(f"  KW {p.pk} cat={p.category.pathstring if p.category else '-'} "
          f"desc={(p.description or '')[:80]!r} name={p.name[:60]!r}")
have = act.exclude(image="").exclude(image__isnull=True).count()
print(f"coverage: {have}/{act.count()} active parts have an image")
for po in PurchaseOrder.objects.order_by("-pk")[:4]:
    print(f"PO {po.reference} sref={po.supplier_reference} status={po.status} "
          f"supplier={po.supplier.name if po.supplier else '-'}")
