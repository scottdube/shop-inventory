"""Search parts across every field a duplicate could be hiding in.

Rule 2 of the enrich job: parts were renamed to canonical form, so a vendor
title will NOT match by name. A duplicate has to be hunted across name,
description (which stores the vendor title as `orig: ...`), IPN, keywords and
supplier SKU — checking only one of those is how the PWM servo driver and the
logic level converter each got entered twice.

Read-only. Give it terms; it ORs them across all of the above.
"""
import argparse
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("terms", nargs="+")
a = ap.parse_args()

q = Q()
for t in a.terms:
    q |= (Q(name__icontains=t) | Q(description__icontains=t) | Q(IPN__icontains=t)
          | Q(keywords__icontains=t) | Q(supplier_parts__SKU__icontains=t))

hits = Part.objects.filter(q).distinct().order_by("pk")
print(f"{hits.count()} hit(s) for {a.terms}")
for p in hits:
    sk = ", ".join(f"{sp.supplier}:{sp.SKU}" for sp in p.supplier_parts.all()[:3])
    print(f"#{p.pk}  active={p.active}  {p.name[:60]}")
    print(f"      cat={p.category.pathstring if p.category else '-'}  IPN={p.IPN!r}")
    print(f"      desc={(p.description or '')[:110]}")
    if sk:
        print(f"      suppliers={sk}")
