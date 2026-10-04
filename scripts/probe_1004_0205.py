"""Read-only probe, 02:05 run 2026-10-04: Haas Tooling order 1000523832.

Which of the eight SKUs already have a supplier part / part, how the existing
Haas parts are named and filed, and the inflow since #1268 for queues A and D.
"""
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from part.models import Part  # noqa: E402

ORDER = "1000523832"
SKUS = ["03-0570", "03-0085", "03-0392", "03-0575", "03-0086",
        "03-0613", "03-0612", "03-0611"]

dup = PurchaseOrder.objects.filter(Q(supplier_reference=ORDER) | Q(reference=ORDER))
print(f"PO for {ORDER}: {[p.reference for p in dup] or 'none'}")
print(f"next PO reference: {PurchaseOrder.generate_reference()}")

haas = Company.objects.get(pk=5)
print(f"\nHaas company #{haas.pk} {haas.name}")
for sp in SupplierPart.objects.filter(supplier=haas).select_related("part").order_by("SKU"):
    p = sp.part
    print(f"  sp #{sp.pk} {sp.SKU:10} pack={sp.pack_quantity!r} link={sp.link!r}")
    print(f"     part #{p.pk} active={p.active} {p.name!r} "
          f"cat={p.category.pathstring if p.category else None} IPN={p.IPN!r} "
          f"img={'Y' if p.image else 'N'} stock={p.total_stock}")

print("\nSKU matches anywhere (sp SKU / MPN, part IPN / description):")
for s in SKUS:
    sps = SupplierPart.objects.filter(SKU__iexact=s)
    parts = Part.objects.filter(Q(IPN__iexact=s) | Q(description__icontains=s)
                                | Q(name__icontains=s) | Q(keywords__icontains=s))
    print(f"  {s}: sp={[ (x.pk, x.supplier.name, x.part_id) for x in sps]} "
          f"parts={[(x.pk, x.active, x.name) for x in parts]}")

print("\nPrior PO lines for these SKUs:")
for li in PurchaseOrderLineItem.objects.filter(part__SKU__in=SKUS).select_related("order"):
    print(f"  {li.order.reference} {li.part.SKU} qty={li.quantity} price={li.purchase_price}")

print("\nCandidate dupes by shape (3/8 or 1/2 carbide end mills, chamfer mills):")
q = (Q(name__icontains="end mill") | Q(name__icontains="endmill")
     | Q(name__icontains="chamfer"))
for p in Part.objects.filter(q).order_by("pk"):
    sps = [(x.supplier.name, x.SKU) for x in p.supplier_parts.all()]
    print(f"  #{p.pk} active={p.active} {p.name!r} "
          f"cat={p.category.pathstring if p.category else None} sp={sps}")

print("\nInflow since #1268 (queues A/D):")
new = Part.objects.filter(pk__gt=1268).order_by("pk")
print(f"  {new.count()} parts")
for p in new:
    sps = [(x.supplier.name, x.SKU, bool(x.link)) for x in p.supplier_parts.all()]
    print(f"  #{p.pk} active={p.active} img={'Y' if p.image else 'N'} "
          f"kw={'Y' if (p.keywords or '').strip() else 'N'} link={'Y' if p.link else 'N'} "
          f"{p.name!r} sp={sps}")

empty_kw = Part.objects.filter(active=True).filter(Q(keywords__isnull=True) | Q(keywords=""))
print(f"\nactive parts with empty keywords: {empty_kw.count()}")
for p in empty_kw[:100]:
    print(f"  #{p.pk} {p.name!r}")
act = Part.objects.filter(active=True)
print(f"image coverage: {act.exclude(image='').exclude(image__isnull=True).count()}/{act.count()} active")
