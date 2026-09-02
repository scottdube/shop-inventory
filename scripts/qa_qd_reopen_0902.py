"""Have queues A and D been REOPENED by parts created since they were closed?

Both were closed against a snapshot of the catalogue. Queue A's closure measured
494 imageless parts on 2026-09-01 and accounted for all 79 that had any URL at
all; queue D's closure measured the keyword backfill down to 37 deliberate
tombstones. Neither statement covers a part created afterwards -- and the
2026-09-01 16:46 run created three Amazon POs, whose ASINs are LIVE listings
rather than the delisted ones that closed the Amazon pool.

A closure is a statement about a set, not a promise about the future. So
re-measure rather than trusting either closure to still hold.

Read-only.
"""
import os
import sys
from datetime import date, timedelta

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from part.models import Part  # noqa: E402

active = Part.objects.filter(active=True)
print(f"active parts: {active.count()}")

noimg = active.filter(image="") | active.filter(image=None)
noimg = noimg.distinct()
print(f"active parts with no image: {noimg.count()}")

nokw = active.filter(keywords="") | active.filter(keywords=None)
nokw = nokw.distinct()
print(f"active parts with empty keywords: {nokw.count()}")

print("\n=== empty-keyword parts (queue D closed at 37 deliberate tombstones) ===")
for p in nokw.order_by("pk"):
    marker = ""
    blob = f"{p.name} {p.description}".upper()
    for w in ["MERGED", "DUPLICATE", "REFUNDED", "NOT INVENTORY", "RETIRED"]:
        if w in blob:
            marker = f"  <tombstone: {w}>"
            break
    print(f"  pk={p.pk:4d} {p.name[:56]:56s}{marker}")

print("\n=== parts on OPEN (Placed/Pending) purchase orders that have no image ===")
open_pos = PurchaseOrder.objects.exclude(status=30).exclude(status=40)  # not complete/cancelled
seen = {}
for po in open_pos:
    for ln in po.lines.all():
        sp = ln.part
        if not sp or not sp.part:
            continue
        p = sp.part
        if p.image:
            continue
        seen.setdefault(p.pk, (p, sp, po))
print(f"  {len(seen)} imageless parts on open POs")
for pk, (p, sp, po) in sorted(seen.items()):
    print(f"  pk={pk:4d} {po.reference} {po.get_status_display():8s} "
          f"supplier={str(po.supplier)[:16]:16s} sku={sp.SKU[:16]:16s} link={bool(p.link)} "
          f"| {p.name[:40]}")

print("\n=== imageless parts created in the last 14 days (any PO state) ===")
cutoff = date.today() - timedelta(days=14)
recent = noimg.filter(creation_date__gte=cutoff).order_by("pk")
print(f"  {recent.count()} parts")
for p in recent:
    sps = list(SupplierPart.objects.filter(part=p))
    print(f"  pk={p.pk:4d} created={p.creation_date} link={bool(p.link)} "
          f"skus={[(str(s.supplier), s.SKU) for s in sps]} | {p.name[:40]}")
