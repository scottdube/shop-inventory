"""Read-only probe for eBay order 09-15252-57599 (vintage Radio Shack strobe).

Duplicate scan across name/description/IPN/SKU, plus the categories a strobe
light could sit in, so po_1004_strobe.py picks one by precedent.
"""
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402

ITEM_ID = "188532551761"

print("== duplicate scan")
q = (Q(name__icontains="strobe") | Q(description__icontains="strobe")
     | Q(name__icontains="radio shack") | Q(name__icontains="radioshack")
     | Q(IPN=ITEM_ID) | Q(keywords__icontains="strobe"))
for p in Part.objects.filter(q).distinct():
    print(f"  #{p.pk} active={p.active} cat={p.category.pathstring if p.category else None} | {p.name}")
for sp in SupplierPart.objects.filter(SKU=ITEM_ID):
    print(f"  !! sp #{sp.pk} SKU {sp.SKU} -> part #{sp.part_id}")

print("\n== categories matching light/lamp/vintage/radio/test")
for c in PartCategory.objects.all():
    s = c.pathstring.lower()
    if any(k in s for k in ("light", "lamp", "vintage", "radio", "led", "test", "equipment", "tools")):
        print(f"  pk {c.pk:4} {c.pathstring} ({c.parts.count()} parts)")

print("\n== where the Science Fair 75-in-1 (eBay Radio Shack precedent) lives")
for p in Part.objects.filter(name__icontains="Science Fair"):
    print(f"  #{p.pk} {p.category.pathstring} | {p.name}")
