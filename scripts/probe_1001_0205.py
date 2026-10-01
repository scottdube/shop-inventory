#!/usr/bin/env python3
"""Read-only probe, 2026-10-01 02:05 overnight run.

  1. Two Amazon refunds landed 2026-09-30: "Monoprice DisplayPort 1.2 to..."
     ($44.99, refund $37.64 -- matches PO-0165 by price) and "4K Display Port
     to Mini HDMI" ($12.99). Which POs carry them, and was stock received?
  2. Queue A/D pools: parts created since #1266, active parts with empty
     keywords, imageless active parts on open POs.

Writes nothing.
"""
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django  # noqa: E402

django.setup()

from django.db.models import Q  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem  # noqa: E402

print("=== PO lines for DisplayPort / Mini HDMI parts ===")
lines = PurchaseOrderLineItem.objects.filter(
    Q(part__part__name__icontains="displayport")
    | Q(part__part__name__icontains="mini hdmi")
    | Q(part__part__name__icontains="minihdmi")
    | Q(part__part__name__icontains="monoprice")
    | Q(part__part__description__icontains="mini hdmi")
).select_related("order", "part__part")
for ln in lines.order_by("order__reference"):
    po = ln.order
    p = ln.part.part
    stock = StockItem.objects.filter(part=p).count()
    qty = sum(s.quantity for s in StockItem.objects.filter(part=p))
    print(f"  {po.reference} status={po.get_status_display()} "
          f"sref={po.supplier_reference!r} part #{p.pk} {p.name!r} "
          f"qty={ln.quantity} recv={ln.received} price={ln.purchase_price} "
          f"| part stock rows={stock} qty={qty} active={p.active}")

print()
print("=== parts created after #1266 ===")
for p in Part.objects.filter(pk__gt=1266).order_by("pk"):
    print(f"  #{p.pk} active={p.active} img={bool(p.image)} "
          f"kw={bool(p.keywords)} {p.name!r}")

print()
empty_kw = Part.objects.filter(active=True).filter(
    Q(keywords__isnull=True) | Q(keywords=""))
print(f"=== active parts with empty keywords: {empty_kw.count()} ===")
for p in empty_kw.order_by("pk")[:20]:
    print(f"  #{p.pk} {p.name!r}")

print()
open_pos = PurchaseOrder.objects.filter(status__in=[10, 20])  # pending, placed
print(f"=== open POs: {open_pos.count()} ===")
for po in open_pos.order_by("reference"):
    for ln in po.lines.all():
        p = ln.part.part if ln.part else None
        if p is not None and not p.image:
            print(f"  {po.reference} part #{p.pk} NO IMAGE {p.name!r}")

total = Part.objects.filter(active=True).count()
imaged = Part.objects.filter(active=True).exclude(image="").exclude(
    image__isnull=True).count()
print()
print(f"coverage: {imaged}/{total} active parts imaged")
