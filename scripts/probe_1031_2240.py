"""Queue C, 22:40 daytime sweep 2026-10-31: READ-ONLY probe before importing 7 Amazon orders.

For each ASIN: existing Amazon supplier part (by SKU or link), parts whose link carries the
ASIN, and duplicate candidates across name / description / keywords / IPN / supplier SKU.
Writes nothing.
"""
import os
import sys

import django
from django.db.models import Q, Sum

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from part.models import Part  # noqa: E402

ITEMS = [
    ("B008DS16PO", ["tactile", "tact switch", "right angle"], ["6x6", "6 x 6", "6mm"]),
    ("B0GM7T6XWP", ["female header", "header"], ["7 pin", "7-pin", "1x7", "7p"]),
    ("B0CL9KXXZB", ["10k", "10 k"], ["resistor"]),
    ("B08BF91KY3", ["1uf", "1 uf", "105"], ["ceramic", "capacitor", "mlcc"]),
    ("B0CZ71WTV2", ["100uf", "100 uf"], ["25v", "25 v"]),
]

amazon = Company.objects.get(name="Amazon")


def show(p, tag):
    q = p.stock_items.aggregate(s=Sum("quantity"))["s"] or 0
    sps = [(s.pk, s.supplier.name, s.SKU, str(s.pack_quantity), float(s.pack_quantity_native))
           for s in p.supplier_parts.all()]
    print(f"    {tag} part #{p.pk}: {p.name!r} active={p.active} stock={float(q):g} "
          f"cat={p.category_id}:{p.category} ipn={p.IPN!r}\n        link={p.link} sps={sps}")


for asin, a_terms, b_terms in ITEMS:
    print(f"=== {asin}")
    for sp in SupplierPart.objects.filter(Q(SKU__iexact=asin) | Q(link__icontains=asin)):
        print(f"  SP #{sp.pk} supplier={sp.supplier.name} SKU={sp.SKU} pack={sp.pack_quantity} "
              f"native={sp.pack_quantity_native} -> part #{sp.part_id}")
    for p in Part.objects.filter(Q(link__icontains=asin) | Q(description__icontains=asin)):
        show(p, "LINK")
    qa = Q()
    for t in a_terms:
        qa |= (Q(name__icontains=t) | Q(description__icontains=t) | Q(keywords__icontains=t)
               | Q(IPN__icontains=t))
    qb = Q()
    for t in b_terms:
        qb |= (Q(name__icontains=t) | Q(description__icontains=t) | Q(keywords__icontains=t))
    hits = Part.objects.filter(qa).filter(qb).distinct()
    print(f"  {hits.count()} candidates")
    for p in hits[:25]:
        show(p, "cand")
