"""Read-only: do the laser-project tumblers and acrylic sign bases have parts / POs?

Scott 2026-11-01: the tumblers in Cab5 and the acrylic sign bases (lit and unlit)
are stock for laser projects, bought on Amazon. Search by the requirement
(tumbler, sign base, acrylic, LED base), not a part number.
"""
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrderLineItem  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem  # noqa: E402

TERMS = ["tumbler", "sign base", "led base", "acrylic", "light base", "night light"]
q = Q()
for t in TERMS:
    q |= Q(name__icontains=t) | Q(description__icontains=t) | Q(keywords__icontains=t)

for p in Part.objects.filter(q).order_by("pk"):
    rows = StockItem.objects.filter(part=p)
    print(f"part {p.pk}  active={p.active}  {p.name[:70]}")
    print(f"     cat: {p.category.pathstring if p.category else '-'}")
    for r in rows:
        print(f"     stock {r.pk}: {float(r.quantity):g} @ "
              f"{r.location.pathstring if r.location else 'NO LOCATION'}")
    for ln in PurchaseOrderLineItem.objects.filter(part__part=p).select_related("order"):
        o = ln.order
        print(f"     {o.reference} status={o.status} {o.supplier_reference} "
              f"qty {float(ln.quantity):g} recv {float(ln.received):g} {o.issue_date}")
