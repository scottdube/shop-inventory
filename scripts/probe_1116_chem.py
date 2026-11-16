#!/usr/bin/env python3
"""Read-only 2026-11-16 02:05: before queueing DIYChemicals order #82397
(heptane 1 gal + 99% IPA 1 gal), see whether the install already tracks
solvents -- an IPA / heptane / alcohol part, a DIYChemicals company, or a
PO carrying 82397. Decides whether this is a reorder of a tracked consumable
or a new-vendor question for Scott.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company  # noqa: E402
from django.db.models import Q  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from part.models import Part  # noqa: E402

terms = ["isopropyl", "IPA ", "alcohol", "heptane", "solvent", "acetone"]
q = Q()
for t in terms:
    q |= Q(name__icontains=t) | Q(description__icontains=t) | Q(keywords__icontains=t)
for p in Part.objects.filter(q).order_by("pk"):
    print(f"PART {p.pk} active={p.active} cat={p.category.pathstring if p.category else '-'} "
          f"name={p.name[:70]!r} desc={(p.description or '')[:90]!r}")
for c in Company.objects.filter(Q(name__icontains="chem") | Q(website__icontains="chem")):
    print(f"COMPANY {c.pk} {c.name!r} web={c.website or '-'}")
for po in PurchaseOrder.objects.filter(
        Q(supplier_reference__icontains="82397") | Q(description__icontains="82397")):
    print(f"PO {po.reference} sref={po.supplier_reference} status={po.status}")
print("done")
