"""Dupe probe for DigiKey sales order 102638220 (2026-11-02) before any write.

Three lines, all values Scott bought on Amazon 2026-10-31 too (POs 0276-0282),
so a part for each identity probably exists already. Lists candidates with
their supplier parts so the PO script can reuse the part and add only a
DigiKey supplier part. Read-only.
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

PROBES = {
    "100uF 25V radial electrolytic (732-9170-1-ND / 860040473003)":
        ["860040473003", "732-9170", "100uF 25V", "100UF 25V", "100 uF 25V"],
    "10k 5% 1/4W carbon film axial (CF14JT10K0CT-ND / CF14JT10K0)":
        ["CF14JT10K0", "CF14JT10K", "10k 5%", "10K 5%", "Resistor 10k", "10KΩ"],
    "Tactile SPST-NO right angle (TS11-674-80-BK-160-RA-D)":
        ["TS11-674", "TS11", "Right Angle Tactile", "right-angle tactile",
         "tactile switch", "tact switch", "Tactile"],
}

for label, terms in PROBES.items():
    q = Q()
    for t in terms:
        q |= (Q(name__icontains=t) | Q(description__icontains=t)
              | Q(IPN__icontains=t) | Q(keywords__icontains=t))
    parts = Part.objects.filter(q).distinct().order_by("pk")
    print(f"\n== {label}: {parts.count()} candidates")
    for p in parts[:25]:
        cat = p.category.pathstring if p.category else "-"
        print(f"  #{p.pk} active={p.active} IPN={p.IPN!r} cat={cat}")
        print(f"      name: {p.name}")
        print(f"      desc: {(p.description or '')[:140]}")
        for sp in SupplierPart.objects.filter(part=p):
            print(f"      sp #{sp.pk} {sp.supplier.name} SKU={sp.SKU} "
                  f"pack={sp.pack_quantity}/{sp.pack_quantity_native}")

for sku in ["732-9170-1-ND", "CF14JT10K0CT-ND", "2223-TS11-674-80-BK-160-RA-D-ND"]:
    hit = SupplierPart.objects.filter(SKU=sku)
    print(f"\nSKU {sku}: {[ (s.pk, s.part_id) for s in hit ] or 'none'}")
