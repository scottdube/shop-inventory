"""Duplicate probe for the 2026-08-26 daytime sweep.

Section 3 says: check for a duplicate across name, description, IPN and
supplier SKU BEFORE creating a part. Two importers have already entered the
same item twice under different names, so the probe is deliberately wide --
it searches on distinctive TOKENS, not on the full vendor title, because the
full title is exactly what differs between two entries of the same thing.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part
from company.models import SupplierPart, Company

PROBES = {
    "chipquik-solder-wire": ["SMDSWLTLFP32", "Chip Quik", "ChipQuik", "low temp solder", "solder wire"],
    "hakko-n61-10": ["N61-10", "N6110", "1.6mm", "desoldering nozzle"],
    "hakko-n61-06": ["N61-06", "N6106", "1.3mm", "desoldering nozzle"],
}

for label, tokens in PROBES.items():
    print(f"\n=== {label}")
    seen = set()
    for tok in tokens:
        qs = Part.objects.filter(name__icontains=tok) | \
             Part.objects.filter(description__icontains=tok) | \
             Part.objects.filter(IPN__icontains=tok) | \
             Part.objects.filter(keywords__icontains=tok)
        for p in qs.distinct()[:12]:
            if p.pk in seen:
                continue
            seen.add(p.pk)
            print(f"  [{tok:>18}] part {p.pk}: {p.name}  (cat={p.category})")
        sps = SupplierPart.objects.filter(SKU__icontains=tok)[:12]
        for sp in sps:
            print(f"  [{tok:>18}] SKU {sp.SKU} -> part {sp.part_id} {sp.part.name} ({sp.supplier})")
    if not seen:
        print("  (no candidate matches)")

print("\n=== Amazon company")
for c in Company.objects.filter(name__icontains="amazon"):
    print(f"  {c.pk}: {c.name}  is_supplier={c.is_supplier}")
