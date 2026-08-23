"""Dump the next N parts whose keywords field is empty, for queue D.

The filter matters. An earlier run used `keywords__in=["", None]`, which
**silently misses SQL NULL** and under-reported the backlog by hundreds. The
correct predicate is Q(keywords="") | Q(keywords__isnull=True); it is spelled
out here so nobody re-derives the broken version.

Emits TSV: pk, category path, name, description (truncated). Read-only.
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
ap.add_argument("--limit", type=int, default=75)
ap.add_argument("--after", type=int, default=0, help="only parts with pk > this")
a = ap.parse_args()

EMPTY = Q(keywords="") | Q(keywords__isnull=True)
qs = Part.objects.filter(EMPTY).filter(pk__gt=a.after).order_by("pk")

print(f"# remaining empty: {Part.objects.filter(EMPTY).count()} / {Part.objects.count()}")
for p in qs[: a.limit]:
    cat = p.category.pathstring if p.category else ""
    desc = (p.description or "").replace("\t", " ").replace("\n", " ")[:170]
    name = (p.name or "").replace("\t", " ")
    print(f"{p.pk}\t{cat}\t{name}\t{desc}")
