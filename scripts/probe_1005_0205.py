"""Read-only probe for the 2026-10-05 02:05 overnight run.

Queue A inflow: every part created since #1324 (last night's high-water mark),
with image/link/keywords state and supplier SKUs. Plus the open-PO image pool
and the count of active parts with empty keywords (queue D).
"""
import os, sys, django
from django.db.models import Q
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from order.models import PurchaseOrder

print("=== parts with pk > 1324 ===")
for p in Part.objects.filter(pk__gt=1324).order_by("pk").prefetch_related("supplier_parts__supplier"):
    sps = "  ".join(f"{sp.supplier.name if sp.supplier else '?'}:{sp.SKU}|{(sp.link or '')[:70]}"
                    for sp in p.supplier_parts.all())
    print(f"{p.pk}\tactive={p.active}\timg={'Y' if p.image else '-'}\tkw={'Y' if p.keywords else '-'}"
          f"\tIPN={p.IPN!r}\t{p.name[:60]}\n\tlink={p.link!r}\n\tsp: {sps}")

print("\n=== open-PO parts without an image ===")
open_pos = PurchaseOrder.objects.filter(status__in=[10, 20, 25])  # pending, placed, on hold
seen = set()
for po in open_pos.order_by("pk"):
    for line in po.lines.all():
        sp = line.part
        if not sp or not sp.part or sp.part.pk in seen:
            continue
        p = sp.part
        seen.add(p.pk)
        if not p.image:
            print(f"{po.reference}\t{p.pk}\t{sp.supplier.name}:{sp.SKU}\t{p.name[:60]}")

act = Part.objects.filter(active=True)
have = act.exclude(image="").exclude(image__isnull=True).count()
print(f"\ncoverage: {have}/{act.count()} active parts have an image")
kw_empty = act.filter(Q(keywords="") | Q(keywords__isnull=True))
print(f"active parts with empty keywords: {kw_empty.count()}")
for p in kw_empty.order_by("pk")[:80]:
    print(f"  kw-empty {p.pk}\t{p.name[:70]}")
