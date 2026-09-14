"""Duplicate probe before creating the ZeniKon DP->Mini HDMI cable part.

Queue C, 22:40 sweep 2026-09-13. Amazon order 113-0032375-3000231 is one
line: a DisplayPort to Mini-HDMI cable. Several display-adapter parts were
created in the last four days (two Monoprice MST hubs, a micro-HDMI lead),
so search by REQUIREMENT -- every display-cable-shaped part -- not by the
part number we already picked, which would return a confident false
negative.
"""
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from part.models import Part  # noqa: E402

TERMS = ["displayport", "display port", " dp ", "mini hdmi", "minihdmi",
         "micro hdmi", "hdmi", "mst"]

q = Q()
for t in TERMS:
    q |= Q(name__icontains=t) | Q(description__icontains=t) | Q(keywords__icontains=t)

print("=== parts matching any display-cable term ===")
for p in Part.objects.filter(q).order_by("pk"):
    print(f"  pk {p.pk:4d}  active={p.active}  [{p.category}]  {p.name}")
    print(f"        desc: {p.description[:150]}")

print("\n=== supplier parts whose SKU/name mentions these ===")
for sp in SupplierPart.objects.filter(
        Q(SKU__icontains="hdmi") | Q(note__icontains="hdmi")
        | Q(part__name__icontains="hdmi")).order_by("pk"):
    print(f"  sp {sp.pk:4d}  {sp.supplier.name:12s} SKU={sp.SKU:16s} -> "
          f"part {sp.part.pk} {sp.part.name}")

print("\n=== is this exact ASIN already a supplier part? ===")
for asin in ["B0GZVWP2JF"]:
    hit = SupplierPart.objects.filter(SKU=asin)
    print(f"  {asin}: {hit.count()} hit(s) {[s.pk for s in hit]}")
