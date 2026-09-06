"""Find the right category for a consumable primary cell (AAA alkaline).

Read-only. Prints the category tree branches that could plausibly hold a
battery, plus any part that is itself a cell/battery, so the choice is made
against precedent rather than invented.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402

print("=== categories matching power/batter/consumable/electrical ===")
for c in PartCategory.objects.all().order_by("pathstring"):
    p = c.pathstring.lower()
    if any(k in p for k in ("power", "batter", "consumable", "cell", "electrical")):
        print(f"  {c.pk:4d}  {c.pathstring}   (parts={c.parts.count()})")

print()
print("=== top-level categories ===")
for c in PartCategory.objects.filter(parent=None).order_by("name"):
    print(f"  {c.pk:4d}  {c.pathstring}")

print()
print("=== parts that are actually cells/batteries ===")
for p in Part.objects.filter(active=True).order_by("pk"):
    blob = f"{p.name} {p.description}".lower()
    if any(k in blob for k in ("aa batter", "aaa", "alkaline", "cr20", "18650",
                               "lipo", "9v batter", "coin cell", "primary cell")):
        cat = p.category.pathstring if p.category else "(none)"
        loc = p.default_location.pathstring if p.default_location else "(none)"
        print(f"  #{p.pk:5d}  {p.name[:58]:58s}  cat={cat}  default_loc={loc}")
