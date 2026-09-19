"""Read-only: what actually lives in the candidate categories, and the top of
the tree, so the two 22:40 parts get filed by precedent rather than by taste.

  - biaze Mini DP -> DP adapter: Electronics/Cables (#119) vs
    Electronics/Connectors/Adapters (#127)
  - NVIDIA T400 GPU: nothing obvious exists; print the top level and anything
    computer-ish so the choice is made against real siblings.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402

for pk in (119, 127, 124, 135):
    c = PartCategory.objects.get(pk=pk)
    print(f"--- #{pk} {c.pathstring}")
    for p in Part.objects.filter(category=c).order_by("pk"):
        print(f"      #{p.pk} {p.name}")

print()
print("=== TOP-LEVEL CATEGORIES (parent is null)")
for c in PartCategory.objects.filter(parent__isnull=True).order_by("name"):
    direct = Part.objects.filter(category=c).count()
    print(f"  #{c.pk:3d} {c.name}  (direct parts: {direct})")

print()
print("=== ANYTHING COMPUTER / PC / BOARD-LEVEL (a home for a GPU?)")
for c in PartCategory.objects.all().order_by("pathstring"):
    p = c.pathstring.lower()
    if any(k in p for k in ("comput", "pc", "single board", "sbc", "card",
                            "periph", "storage", "memory", "module")):
        print(f"  #{c.pk:3d} {c.pathstring}  ({Part.objects.filter(category=c).count()})")

print()
print("=== parts whose name smells like a whole-computer assembly")
q = (Part.objects.filter(name__icontains="raspberry")
     | Part.objects.filter(name__icontains="mini pc")
     | Part.objects.filter(name__icontains="motherboard")
     | Part.objects.filter(name__icontains="SSD")
     | Part.objects.filter(name__icontains="NUC")
     | Part.objects.filter(name__icontains="PCIe")).distinct()
for d in q:
    print(f"  #{d.pk} cat={d.category} | {d.name}")
