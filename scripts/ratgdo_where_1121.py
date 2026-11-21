"""Read-only: where are the rat-ratgdo boards and their components?

Finds parts matching ratgdo terms, prints each stock item with its location
path (SLN vs LRD), plus any BOM under a matching assembly and where each BOM
line's stock sits. Also prints florida earmark metadata if present.
"""
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, BomItem  # noqa: E402
from stock.models import StockItem  # noqa: E402

TERMS = ["ratgdo", "rat-ratgdo", "garage door"]
q = Q()
for t in TERMS:
    q |= Q(name__icontains=t) | Q(description__icontains=t) | Q(keywords__icontains=t) | Q(IPN__icontains=t)
parts = Part.objects.filter(q).distinct()


def stock_lines(p):
    out = []
    for si in StockItem.objects.filter(part=p):
        loc = si.location.pathstring if si.location else "(no location)"
        md = si.metadata or {}
        out.append(f"    stock pk={si.pk} qty={si.quantity} loc={loc} status={si.status} md={md if md else ''} notes={(si.notes or '')[:120]!r}")
    return out


print(f"MATCHING PARTS: {parts.count()}")
for p in parts:
    print(f"- pk={p.pk} name={p.name!r} active={p.active} assembly={p.assembly} cat={p.category.pathstring if p.category else None}")
    print(f"  desc={(p.description or '')[:160]!r} md={p.metadata or ''}")
    for line in stock_lines(p):
        print(line)
    if p.assembly:
        bom = BomItem.objects.filter(part=p)
        print(f"  BOM lines: {bom.count()}")
        for b in bom:
            sp = b.sub_part
            print(f"   * {b.quantity} x {sp.name!r} (pk={sp.pk})")
            for line in stock_lines(sp):
                print("  " + line)

# Stock items whose notes/metadata mention ratgdo even if the part does not
print("\nSTOCK ITEMS MENTIONING ratgdo IN NOTES/BATCH/METADATA:")
for si in StockItem.objects.filter(Q(notes__icontains="ratgdo") | Q(batch__icontains="ratgdo")):
    loc = si.location.pathstring if si.location else "(no location)"
    print(f"  pk={si.pk} part={si.part.name!r} qty={si.quantity} loc={loc}")
for si in StockItem.objects.exclude(metadata=None):
    if "ratgdo" in str(si.metadata).lower():
        loc = si.location.pathstring if si.location else "(no location)"
        print(f"  md-hit pk={si.pk} part={si.part.name!r} qty={si.quantity} loc={loc} md={si.metadata}")
