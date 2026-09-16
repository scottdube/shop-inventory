"""Read part #1176 (Alkaline Battery AAA) and its supplier part, to copy the
pack/category/naming precedent onto a D-cell part from the same Amazon Basics
Subscribe & Save shape. Read-only."""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from part.models import Part  # noqa: E402

p = Part.objects.get(pk=1176)
print(f"part #{p.pk}  {p.name}")
print(f"  category      {p.category.pathstring if p.category else None}")
print(f"  IPN           {p.IPN}")
print(f"  units         {p.units!r}")
print(f"  description   {p.description}")
print(f"  keywords      {p.keywords!r}")
print(f"  default_loc   {p.default_location}")
print(f"  component={p.component} purchaseable={p.purchaseable} "
      f"assembly={p.assembly}")

for sp in SupplierPart.objects.filter(part=p):
    print(f"  sp #{sp.pk} supplier={sp.supplier.name} SKU={sp.SKU}")
    print(f"     pack_quantity={sp.pack_quantity!r} "
          f"native={sp.pack_quantity_native!r}")
    print(f"     link={sp.link}")
    print(f"     note={sp.note!r}")

# Which POs bought it, and at what line price / qty?
from order.models import PurchaseOrderLineItem  # noqa: E402
for li in PurchaseOrderLineItem.objects.filter(part__part=p):
    print(f"  line: {li.order.reference} ref={li.order.supplier_reference} "
          f"qty={li.quantity} price={li.purchase_price}")

# Does a D-cell part already exist under any spelling?
print("\n-- duplicate scan for D cell --")
for term in ["D Cell", "D-Cell", "LR20", "B0BTW1N3TV"]:
    hits = Part.objects.filter(name__icontains=term) | \
        Part.objects.filter(description__icontains=term) | \
        Part.objects.filter(IPN__icontains=term)
    for h in hits.distinct():
        print(f"  {term!r}: #{h.pk} active={h.active} {h.name}")
    else:
        pass
print("  (no line above = no hit)")
