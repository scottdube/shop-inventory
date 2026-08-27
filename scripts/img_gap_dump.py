"""Dump every imageless part with its supplier SKUs, as CSV, for eyeballing.

`image_backlog.py` answers "how many, and from whom" — the shape of the queue.
This answers the different question Scott asked on 2026-08-27: *show me the
actual SKUs and descriptions so I can look*. The prompt for it was the
AliExpress reversal — three queue-A rulings-out ("the SKU is not a product ID,
so there is nothing to look up") rest on the same reasoning that had just been
shown wrong, and a count cannot be checked by eye. A list can.

Emits CSV on stdout, one row per (part, supplier part). Read-only.
"""
import csv
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

NOIMG = Q(image="") | Q(image__isnull=True)

w = csv.writer(sys.stdout)
w.writerow(["pk", "category", "name", "description", "supplier", "sku",
            "part_link", "ipn", "active", "stock"])

for p in Part.objects.filter(NOIMG).distinct().order_by("pk").prefetch_related(
        "supplier_parts__supplier"):
    sps = list(p.supplier_parts.all())
    base = [
        p.pk,
        p.category.pathstring if p.category else "",
        (p.name or "").replace("\n", " "),
        (p.description or "").replace("\n", " "),
    ]
    tail = [p.link or "", p.IPN or "", "yes" if p.active else "NO",
            float(p.total_stock)]
    if not sps:
        w.writerow(base + ["", ""] + tail)
        continue
    for sp in sps:
        w.writerow(base + [sp.supplier.name if sp.supplier else "?",
                           sp.SKU or ""] + tail)
