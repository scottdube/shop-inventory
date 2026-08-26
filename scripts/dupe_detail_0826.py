"""Detail on the duplicate Hakko nozzle parts found by dupe_probe_0826.

Picking which of two identical parts a new PO line should point at is not a
coin flip: the wrong choice strands the purchase history on the copy nobody
uses. Print stock, supplier parts and PO lines for each so the choice is
made on evidence.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402
from stock.models import StockItem  # noqa: E402
from company.models import SupplierPart  # noqa: E402
from order.models import PurchaseOrderLineItem  # noqa: E402

for pk in (86, 213, 87, 214):
    try:
        p = Part.objects.get(pk=pk)
    except Part.DoesNotExist:
        print(f"part {pk}: MISSING")
        continue
    print(f"\n=== part {pk}: {p.name}")
    print(f"  IPN={p.IPN!r}  keywords={p.keywords!r}")
    print(f"  default_location={p.default_location}")
    print(f"  description={p.description[:120]!r}")
    print(f"  notes={(p.notes or '')[:200]!r}")
    for si in StockItem.objects.filter(part=p):
        print(f"  STOCK {si.pk}: qty={si.quantity} loc={si.location} status={si.status}")
    for sp in SupplierPart.objects.filter(part=p):
        print(f"  SUPPLIERPART {sp.pk}: {sp.supplier} SKU={sp.SKU} pack={sp.pack_quantity}")
    for li in PurchaseOrderLineItem.objects.filter(part__part=p):
        print(f"  POLINE {li.pk}: {li.order.reference} supplier_ref={li.order.supplier_reference} "
              f"qty={li.quantity} recv={li.received} price={li.purchase_price}")
