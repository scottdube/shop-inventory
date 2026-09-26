"""Queue C duplicate probe, 22:40 sweep 2026-09-25. Read-only.

Two Amazon orders placed 2026-09-25:
  113-3662169-9294634  DIYhz 20 Pack 5.5x2.1 DC power jack, panel mount  B08CVCJ97Q
  113-0031489-9794658  UL Listed 12V 2A 24W AC/DC adapter, 5 pack         B0DKT5DH2K
Searches name, description, IPN and supplier SKU before anything is created.
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

for asin in ("B08CVCJ97Q", "B0DKT5DH2K"):
    print(f"\n=== {asin}")
    for sp in SupplierPart.objects.filter(SKU__iexact=asin):
        print(f"  SP #{sp.pk} supplier={sp.supplier.name} part #{sp.part.pk} {sp.part.name}")
    for p in Part.objects.filter(Q(IPN__iexact=asin) | Q(description__icontains=asin)):
        print(f"  PART #{p.pk} {p.name}")

TERMS = {
    "jack": ["DC jack", "DC power jack", "barrel jack", "5.5x2.1", "5.5 x 2.1",
             "5.5mm x 2.1", "5.5 mm", "DC socket", "DC-022", "DC-099"],
    "adapter": ["12V 2A", "12 V 2 A", "12V2A", "24W", "wall adapter",
                "power adapter", "AC/DC adapter", "power supply adapter",
                "wall wart"],
}
for key, terms in TERMS.items():
    q = Q()
    for t in terms:
        q |= Q(name__icontains=t) | Q(description__icontains=t) | Q(keywords__icontains=t)
    print(f"\n=== {key} term scan")
    for p in Part.objects.filter(q).distinct().order_by("pk"):
        sps = ", ".join(f"{s.supplier.name}:{s.SKU}(pk{s.pk},pack{s.pack_quantity_native})"
                        for s in p.supplier_parts.all())
        print(f"  #{p.pk} active={p.active} stock={p.total_stock} "
              f"cat={p.category.pathstring if p.category else None}\n"
              f"      {p.name}\n      desc={(p.description or '')[:110]}\n      sp=[{sps}]")
