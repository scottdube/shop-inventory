"""Duplicate probe before creating the Monoprice DP->HDMI MST hub (ASIN B07575NBTV).

Searches name/description/IPN/keywords and SupplierPart.SKU for anything that
could already be this item, plus the video-adapter neighbourhood so the new part
lands in the same category as its precedents rather than a fresh one.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.db.models import Q  # noqa: E402
from part.models import Part  # noqa: E402
from company.models import SupplierPart  # noqa: E402

TERMS = [
    "monoprice", "displayport", "display port", "MST", "multi-stream",
    "HDMI", "B07575NBTV", "hub", "4K", "DP 1.2", "video adapter",
    "splitter", "DisplayPort 1.2",
]

seen = {}
for t in TERMS:
    q = Part.objects.filter(
        Q(name__icontains=t) | Q(description__icontains=t)
        | Q(IPN__icontains=t) | Q(keywords__icontains=t)
    )
    for p in q:
        seen.setdefault(p.pk, p)
    print(f"{t!r:22} parts={q.count()}")

sk = SupplierPart.objects.filter(
    Q(SKU__icontains="B07575NBTV") | Q(SKU__icontains="monoprice")
)
print(f"\nSupplierPart SKU hits: {sk.count()}")
for s in sk:
    print(f"  SP {s.pk} SKU={s.SKU} -> part {s.part_id} {s.part.name[:60]}")

print(f"\n=== {len(seen)} distinct parts matched ===")
for pk in sorted(seen):
    p = seen[pk]
    cat = p.category.pathstring if p.category else "(none)"
    print(f"#{pk:5} act={p.active!s:5} {cat:34} {p.name[:64]}")
    print(f"        IPN={p.IPN!r} desc={p.description[:80]!r}")
