"""Read-only: show supplier parts and PO history for the zip-bag parts 849/850/851."""
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from part.models import Part  # noqa: E402

for pk in (849, 850, 851):
    p = Part.objects.get(pk=pk)
    print(f"part #{p.pk} {p.name!r} active={p.active} link={p.link or '-'} ipn={p.IPN or '-'}")
    print(f"  desc={(p.description or '')[:160]!r}")
    for sp in p.supplier_parts.all():
        print(f"  sp #{sp.pk} supplier={sp.supplier.name} SKU={sp.SKU!r} link={sp.link or '-'} "
              f"pack={sp.pack_quantity} native={sp.pack_quantity_native}")
        for li in sp.purchase_order_line_items.all():
            print(f"    PO {li.order.reference} sref={li.order.supplier_reference} "
                  f"status={li.order.status} qty={li.quantity} price={li.purchase_price}")
for asin in ("B09N32PLTN", "B09MCM8QGK", "B09MVP9MDQ"):
    hits = SupplierPart.objects.filter(Q(SKU__icontains=asin) | Q(link__icontains=asin))
    hp = Part.objects.filter(Q(link__icontains=asin) | Q(IPN__icontains=asin)
                             | Q(description__icontains=asin))
    print(f"{asin}: sps={[(s.pk, s.part_id, s.supplier.name, s.SKU) for s in hits]} "
          f"parts={[p.pk for p in hp]}")
