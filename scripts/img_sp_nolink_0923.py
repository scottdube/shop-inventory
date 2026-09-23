"""Queue A, 2026-09-23: list the imageless parts that have a supplier part but no link.

The 09-22 run measured 513 imageless parts and named this group (61 rows) as the
only route left untried. Before choosing a method, this prints each row with its
supplier, SKU and any SupplierPart.link, so the fetch can be picked per vendor
instead of assumed.

Read-only.
"""
import os
import sys
from collections import Counter

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

NOIMG = Q(image="") | Q(image__isnull=True)

rows = []
for p in Part.objects.filter(NOIMG).distinct().order_by("pk"):
    if (p.link or "").strip():
        continue
    sps = list(p.supplier_parts.select_related("supplier"))
    if not sps:
        continue
    rows.append((p, sps))

by_sup = Counter()
print(f"imageless, no Part.link, has SupplierPart: {len(rows)}")
print(f"  of which active: {sum(1 for p, _ in rows if p.active)}\n")
for p, sps in rows:
    flag = "" if p.active else " [INACTIVE]"
    print(f"{p.pk}{flag}\t{p.name[:80]}")
    for sp in sps:
        sup = sp.supplier.name if sp.supplier else "?"
        by_sup[sup] += 1
        link = (sp.link or "").strip()
        print(f"    sp={sp.pk} {sup} | SKU={sp.SKU!r} | link={link[:90]!r}")

print("\nby supplier:")
for s, n in by_sup.most_common():
    print(f"  {n:>3}  {s}")
