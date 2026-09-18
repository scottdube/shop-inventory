"""Read-only: where does a WiFi access point file?

The nanoHD from Amazon order 113-7781321-8645014 needs a category. Part #930
(MikroTik Metal 2SHPn radio) sits in `RF`, which is the nearest precedent, but
this install carries shadow category roots and the flat side usually wins, so
print the candidates rather than guessing at a pathstring.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402

terms = ("rf", "network", "wireless", "radio", "comm", "module")
seen = set()
for t in terms:
    for c in PartCategory.objects.filter(pathstring__icontains=t):
        if c.pk in seen:
            continue
        seen.add(c.pk)
        print(f"#{c.pk:4d}  {c.pathstring}   parts={c.parts.count()}")

print("\n--- category of the nearest precedent, part #930 ---")
p = Part.objects.get(pk=930)
print(f"#{p.pk} {p.name} -> {p.category.pathstring} (pk={p.category_id})")
print(f"  siblings: {[x.name for x in p.category.parts.all()[:12]]}")
