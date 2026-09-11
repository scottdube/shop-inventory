"""Read-only detail on the two nearest neighbours of the new bar monitor.

#397  VSDISPLAY 10.4" IPS LCD Display  — active=False. Inactive parts on this
      instance are usually MERGE RECEIPTS, so before calling it a tombstone,
      read its stock, its supplier parts and its notes.
#1047 WIMAXIT M1560CTV2 Portable Touchscreen Monitor 15.6in — active, in
      Displays, and the closest thing to a complete standalone monitor already
      on the instance. Its naming shape is the precedent to follow.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402
from company.models import SupplierPart  # noqa: E402
from stock.models import StockItem  # noqa: E402

for pk in (397, 1047):
    p = Part.objects.get(pk=pk)
    print("=" * 72)
    print(f"#{p.pk}  {p.name}")
    print(f"  active      = {p.active}")
    print(f"  category    = {p.category.pathstring if p.category else '(none)'}")
    print(f"  IPN         = {p.IPN!r}")
    print(f"  keywords    = {p.keywords!r}")
    print(f"  default_loc = {p.default_location}")
    print(f"  description = {p.description}")
    print(f"  total stock = {p.total_stock}")
    for si in StockItem.objects.filter(part=p):
        print(f"    stock {si.pk}: qty={si.quantity} loc={si.location} status={si.status}")
    for sp in SupplierPart.objects.filter(part=p):
        print(f"    supplierpart {sp.pk}: {sp.supplier.name} SKU={sp.SKU} "
              f"pack={sp.pack_quantity} link={sp.link}")
    print("  --- notes ---")
    print(p.notes or "  (empty)")
