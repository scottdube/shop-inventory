"""Read-only: candidate categories for the 2026-10-12 22:40 sweep's three Amazon
orders (door latch set x2, Aeotec ZW150 dimmer bypass). Prints where the
precedent parts live (#402 Aeotec Multisensor, #1133 Prime-Line spring) and
every category whose path mentions hardware/home/door/electrical/automation."""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402

for pk in (402, 1133):
    p = Part.objects.get(pk=pk)
    print(f"#{pk} cat={p.category_id} {p.category.pathstring}  | {p.name}")

print()
for c in PartCategory.objects.all().order_by("pathstring"):
    s = c.pathstring.lower()
    if any(k in s for k in ("hardware", "home", "door", "electrical", "automation",
                            "z-wave", "zwave", "smart", "lighting", "mechanical", "building")):
        print(f"{c.pk:4d}  parts={c.parts.count():3d}  {c.pathstring}")
