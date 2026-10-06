"""Read-only lookup for the 22:40 sweep 2026-10-05: duplicate check and
category candidates for a cable-tie tool before writing a PO."""
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402

terms = ["cable tie", "zip tie", "tie tool", "tension", "Lasnten", "Juuqiaerw", "cable cutter", "flush cut"]
q = Q()
for t in terms:
    q |= Q(name__icontains=t) | Q(description__icontains=t) | Q(keywords__icontains=t)
print("== parts matching", terms)
for p in Part.objects.filter(q).order_by("pk"):
    print(f"  #{p.pk} active={p.active} [{p.category.pathstring if p.category else '-'}] {p.name}")
print("== supplier parts matching")
for sp in SupplierPart.objects.filter(Q(SKU__icontains="B0") & (Q(description__icontains="cable tie") | Q(description__icontains="zip tie"))):
    print(f"  sp#{sp.pk} {sp.SKU} {sp.description} -> part #{sp.part_id}")
print("== categories under Tooling and any 'Hand'/'Tool' category")
for c in PartCategory.objects.filter(Q(pathstring__istartswith="Tooling") | Q(name__icontains="hand") | Q(name__icontains="tool")).order_by("pathstring"):
    print(f"  {c.pk:4d} {c.pathstring}  parts={c.parts.count()}")
