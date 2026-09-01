"""Pre-create probe for the 2026-09-01 16:40 sweep.

Three new Amazon orders. Before creating anything: check the three ASINs are
not already supplier parts, look for name/description duplicates across the
obvious search terms, and print the candidate categories so the import script
picks a real pathstring rather than guessing one.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.db.models import Q  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from company.models import SupplierPart  # noqa: E402

ASINS = ["B0DCVTTXMJ", "B0FT8BQNVS", "B0FD2MGBZV"]

print("=== ASIN already a SupplierPart? ===")
for a in ASINS:
    sp = SupplierPart.objects.filter(SKU=a).first()
    print(f"  {a}: {'SP ' + str(sp.pk) + ' -> part ' + str(sp.part_id) if sp else 'absent'}")

TERMS = [
    ("battery brush", ["battery brush", "terminal brush", "cleaning brush", "wire brush"]),
    ("battery cable", ["battery cable", "6 awg", "6 gauge", "welding cable", "4 awg"]),
    ("lugs", ["copper lug", "ring terminal", "cable lug", "5/16", "3/8"]),
    ("crimper", ["crimper", "crimping", "crimp tool", "hydraulic crimp", "lug crimp"]),
    ("heat shrink", ["heat shrink", "heatshrink", "shrink tubing"]),
]

print("\n=== duplicate search (name / description / IPN / SKU) ===")
for label, terms in TERMS:
    hits = set()
    for t in terms:
        q = Q(name__icontains=t) | Q(description__icontains=t) | Q(IPN__icontains=t)
        for p in Part.objects.filter(q)[:40]:
            hits.add((p.pk, p.name[:70], p.category.pathstring if p.category else "-"))
        for sp in SupplierPart.objects.filter(SKU__icontains=t)[:20]:
            hits.add((sp.part_id, sp.part.name[:70], "via SKU " + sp.SKU))
    print(f"\n-- {label}: {len(hits)} hit(s)")
    for pk, name, cat in sorted(hits):
        print(f"   #{pk:5}  {name}   [{cat}]")

print("\n=== candidate categories ===")
for c in PartCategory.objects.all().order_by("pathstring"):
    if any(k in c.pathstring.lower() for k in
           ("tool", "cable", "wire", "connector", "terminal", "hardware",
            "consumable", "electr", "power", "hand")):
        print(f"   #{c.pk:4}  {c.pathstring}   ({c.parts.count()} parts)")

print("\n=== 15 most recently created parts (current-practice categories) ===")
for p in Part.objects.order_by("-pk")[:15]:
    print(f"   #{p.pk:5}  {p.category.pathstring if p.category else '-':45}  {p.name[:50]}")
