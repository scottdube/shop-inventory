"""Duplicate + category probe for the 2026-08-30 22:40 sweep's four Amazon orders.

Read-only. Checks each candidate across Part.name, Part.description, Part.IPN
and SupplierPart.SKU before anything is created, per the "check for a duplicate
before creating a part" invariant — two importers have already entered the same
item twice under different names.

Also dumps plausible categories so the new parts land somewhere a human would
have put them, rather than in whatever category the first template happened to
have.
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

CANDIDATES = [
    ("113-2527839-4777829", "B07GPJ6876", "push button switch 22mm momentary",
     ["push button", "pushbutton", "LA38", "momentary", "22mm"]),
    ("113-3553954-0382657", "B0H28L84GL", "water flow sensor YF-S401 hall effect",
     ["flow sensor", "flow meter", "YF-S401", "YF-S", "flow"]),
    ("113-4877215-5009041", "B0GX5HM4X3", "INA228 current voltage power monitor",
     ["INA228", "INA219", "INA226", "current sensor", "power monitor"]),
    ("113-8727025-8809004", "B0B4CBZCBC", "magnetic contactor 25A 24VDC MC-9b",
     ["contactor", "MC-9", "Baomain", "relay 25A"]),
]

for ref, asin, label, terms in CANDIDATES:
    print("=" * 72)
    print(f"{ref}  ASIN={asin}  {label}")

    sp = SupplierPart.objects.filter(SKU=asin).first()
    print(f"  SKU {asin}: {'EXISTS -> part %s %s' % (sp.part_id, sp.part.name) if sp else 'absent'}")

    ipn = Part.objects.filter(IPN=asin).first()
    print(f"  IPN {asin}: {'EXISTS -> %s %s' % (ipn.pk, ipn.name) if ipn else 'absent'}")

    for term in terms:
        q = Part.objects.filter(
            Q(name__icontains=term) | Q(description__icontains=term) | Q(keywords__icontains=term)
        )
        hits = list(q[:6])
        if hits:
            print(f"  term {term!r}:")
            for h in hits:
                print(f"      #{h.pk:5d} [{h.category}] {h.name}")
        else:
            print(f"  term {term!r}: no hits")

print("=" * 72)
print("CATEGORIES containing likely homes:")
for term in ["switch", "sensor", "relay", "contactor", "power", "electromech"]:
    for c in PartCategory.objects.filter(name__icontains=term)[:8]:
        print(f"  #{c.pk:4d}  {c.pathstring}  ({c.parts.count()} parts)")
