#!/usr/bin/env python3
"""Read-only probe, 2026-10-02 02:05 overnight run.

  1. Queue A/D inflow: parts created since #1267, active parts with empty
     keywords, imageless active parts on open POs.
  2. Imageless active parts that still carry a supplier SKU or link, by
     supplier -- the pool queue A could draw on, so a below-floor night can
     say WHY rather than just report a small number.

Writes nothing.
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django  # noqa: E402

django.setup()

from django.db.models import Q  # noqa: E402
from company.models import SupplierPart  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from part.models import Part  # noqa: E402

print("=== parts created after #1267 ===")
for p in Part.objects.filter(pk__gt=1267).order_by("pk"):
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

print()
noimg = Part.objects.filter(active=True).filter(Q(image="") | Q(image__isnull=True))
by_sup = Counter()
for sp in SupplierPart.objects.filter(part__in=noimg).select_related("supplier"):
    if (sp.SKU or "").strip() or (sp.link or "").strip():
        by_sup[sp.supplier.name] += 1
print(f"=== imageless active parts with a supplier SKU/link, by supplier "
      f"(supplier-part rows, all shown) ===")
for name, n in by_sup.most_common():
    print(f"  {n:4d}  {name}")

total = Part.objects.filter(active=True).count()
print()
print(f"coverage: {total - noimg.count()}/{total} active parts imaged")
