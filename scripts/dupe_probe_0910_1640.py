"""Duplicate probe for the 2026-09-10 16:40 sweep — three new Amazon parts.

Read-only. Searches name / description / IPN / keywords / supplier SKU for
anything already covering:

  B075754ZYC  Monoprice DisplayPort 1.2 -> DisplayPort MST hub, 2-port
  B0H3JNGX1D  Vanjua 4-pack 90-degree USB-C male-to-female right-angle adapter
  B07QB6KL85  Amazon Basics 5-pack USB-A to Micro-USB cable, 3 ft

The DP->HDMI MST hub imported yesterday as PO-0163 is deliberately in the term
list: it is a DIFFERENT part (HDMI outputs, not DP) but it is the nearest
neighbour, and this run must name the new one so the two do not read as the
same object on a shelf.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.db.models import Q  # noqa: E402
from part.models import Part  # noqa: E402
from company.models import SupplierPart  # noqa: E402

TERMS = [
    # candidate ASINs — the strongest possible hit
    "B075754ZYC", "B0H3JNGX1D", "B07QB6KL85",
    # MST hub cluster
    "MST", "Multi-Stream", "DisplayPort", "DisplayPort 1.2", "DP hub",
    "Monoprice", "display hub", "video splitter", "daisy chain",
    # USB-C right-angle adapter cluster
    "USB-C", "USB C", "Type-C", "90 degree", "right angle", "right-angle",
    "adapter extender", "Vanjua", "male to female", "100W",
    # micro USB cable cluster
    "Micro USB", "Micro-USB", "USB-A", "charging cable", "Amazon Basics",
    "480Mbps", "USB 2.0",
]

for term in TERMS:
    parts = Part.objects.filter(
        Q(name__icontains=term)
        | Q(description__icontains=term)
        | Q(IPN__icontains=term)
        | Q(keywords__icontains=term)
    ).order_by("pk")
    # MPN lives on ManufacturerPart, not SupplierPart — SupplierPart has SKU,
    # description and note, and reaches the MPN only through manufacturer_part.
    sps = SupplierPart.objects.filter(
        Q(SKU__icontains=term)
        | Q(description__icontains=term)
        | Q(note__icontains=term)
        | Q(manufacturer_part__MPN__icontains=term)
    ).order_by("pk")

    if not parts and not sps:
        continue

    print("=" * 72)
    print(f"TERM {term!r}")
    for p in parts:
        flag = "" if p.active else "  [INACTIVE — merge tombstone]"
        print(f"  part {p.pk:5d}  {p.name[:62]}")
        print(f"            cat={p.category.pathstring if p.category else None} "
              f"IPN={p.IPN}{flag}")
    for sp in sps:
        print(f"  SP   {sp.pk:5d}  SKU={sp.SKU} MPN={sp.MPN} -> part {sp.part_id} "
              f"{sp.part.name[:44]}")

print("=" * 72)
print("probe complete — read the whole set, a negative on one term is not a finding")
