"""Read-only: resolve the category PKs for the 0913 audio/tactile order.

Precedent to follow, not invent: part #52 (Dayton Audio DMA45-4 driver) is
already filed somewhere, and a tactile transducer is the same class of
voice-coil device. Print where #52 lives and what the flat roots look like,
then the equipment-shaped categories for the rack amplifier.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402

p52 = Part.objects.get(pk=52)
print(f"#52 {p52.name}")
print(f"    category pk={p52.category.pk} {p52.category.pathstring}")

print("\nROOT-LEVEL CATEGORIES (the flat side)")
for c in PartCategory.objects.filter(parent__isnull=True).order_by("name"):
    print(f"  pk={c.pk:4d}  {c.name}  (direct parts={c.parts.count()})")

print("\nEQUIPMENT-SHAPED")
for t in ["equipment", "tool", "machine", "instrument", "power", "mech"]:
    for c in PartCategory.objects.filter(name__icontains=t):
        print(f"  pk={c.pk:4d}  {c.pathstring}  (parts={c.parts.count()})")
