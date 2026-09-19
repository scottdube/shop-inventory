"""Queue C probe, 16:40 run 2026-09-19.

Before creating a part for eBay order 27-15157-16681 (Science Fair 75-in-1
Electronic Project Kit, Radio Shack 28-247), find out two things the sweep must
not guess at:

  1. which category a LEARNING/PROJECT KIT belongs in on this instance, and
  2. whether any such part already exists under another name.

Read-only. Writes nothing.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402

print("== categories whose path mentions kit/project/educat/tool ==")
for c in PartCategory.objects.all().order_by("tree_id", "lft"):
    p = c.pathstring.lower()
    if any(w in p for w in ("kit", "project", "educat", "learn", "module")):
        print(f"  pk {c.pk:4d}  {c.pathstring}   parts={c.parts.count()}")

print("\n== existing parts that look like a project/learning kit ==")
q = (Part.objects.filter(name__icontains="kit")
     | Part.objects.filter(name__icontains="science fair")
     | Part.objects.filter(name__icontains="radio shack")
     | Part.objects.filter(name__icontains="project")
     | Part.objects.filter(IPN="227521676914")
     | Part.objects.filter(description__icontains="28-247")).distinct()
for d in q.order_by("pk"):
    cat = d.category.pathstring if d.category else "(none)"
    print(f"  #{d.pk:5d} active={d.active} [{cat}] {d.name}")

print("\n== eBay company + SKU check ==")
ebay = Company.objects.filter(name="eBay").first()
print(f"  company: {ebay.pk if ebay else None} {ebay}")
sp = SupplierPart.objects.filter(supplier=ebay, SKU="227521676914")
print(f"  supplier part for item 227521676914 exists: {sp.exists()}")
print("\n== recent eBay supplier parts (convention check) ==")
for s in SupplierPart.objects.filter(supplier=ebay).order_by("-pk")[:6]:
    print(f"  sp #{s.pk} SKU={s.SKU} pack={s.pack_quantity} part=#{s.part_id} {s.part.name[:60]}")
