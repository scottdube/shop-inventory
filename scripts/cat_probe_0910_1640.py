"""Category placement probe for the 2026-09-10 16:40 sweep. Read-only.

Three parts need a home: a DisplayPort MST hub, a USB-C right-angle adapter,
and a 5-pack of USB-A to Micro-USB cables. Prints the Cables and Modules
subtrees with populations, plus how the existing cable/adapter parts are
actually filed, because on this instance the flat root and the nested root
both exist and precedent beats tidiness.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402

print("=" * 72)
print("CATEGORIES matching cable / adapter / connector / module / video")
for c in PartCategory.objects.all().order_by("pathstring"):
    low = c.pathstring.lower()
    if any(k in low for k in ("cable", "adapter", "connector", "module",
                              "video", "display", "comput")):
        n = Part.objects.filter(category=c, active=True).count()
        print(f"  {c.pk:5d}  {c.pathstring:<52} active_parts={n}")

print("=" * 72)
print("HOW EXISTING CABLES/ADAPTERS ARE ACTUALLY FILED")
for pk in (477, 715, 717, 134, 1174, 1181, 1180, 258, 1047):
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"  part {pk} — does not exist")
        continue
    print(f"  part {p.pk:5d}  {p.name[:56]}")
    print(f"            cat={p.category.pathstring if p.category else None} "
          f"active={p.active}")

print("=" * 72)
print("EVERY ACTIVE PART WHOSE NAME LOOKS LIKE A CABLE OR AN ADAPTER")
for p in Part.objects.filter(active=True).order_by("pk"):
    low = p.name.lower()
    if any(k in low for k in ("cable", "adapter", "cord", "extender", "hub")):
        print(f"  {p.pk:5d}  {p.name[:56]:<56} "
              f"{p.category.pathstring if p.category else None}")
