"""Queue B probe 4 — is the PRICE already recorded for parts #121-#130?

Probe 3 found every part and SupplierPart from the four un-imported orders
already exists WITH stock, so the only thing missing is the PurchaseOrder. That
matters only if the PO is where the price would live. So: print, for each of
these ten parts, every place a cost could be recorded — SupplierPart price
breaks, StockItem.purchase_price, and any PO line referencing it.

Read-only.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart, SupplierPriceBreak  # noqa: E402
from order.models import PurchaseOrderLineItem  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem  # noqa: E402

for pk in range(121, 131):
    try:
        p = Part.objects.get(pk=pk)
    except Part.DoesNotExist:
        print(f"#{pk} MISSING")
        continue
    print(f"\n#{p.pk} {p.name!r}")
    print(f"   cat={p.category}  stock={p.total_stock}  purchaseable={p.purchaseable}")
    for sp in SupplierPart.objects.filter(part=p):
        breaks = list(SupplierPriceBreak.objects.filter(part=sp))
        print(f"   SupplierPart pk={sp.pk} {sp.supplier.name} SKU={sp.SKU!r} "
              f"pack={sp.pack_quantity!r} native={sp.pack_quantity_native} "
              f"breaks={[(str(b.quantity), str(b.price)) for b in breaks] or 'NONE'}")
    for si in StockItem.objects.filter(part=p):
        print(f"   StockItem pk={si.pk} qty={si.quantity} loc={si.location} "
              f"purchase_price={si.purchase_price} po={si.purchase_order} "
              f"stocktake={si.stocktake_date}")
    lines = PurchaseOrderLineItem.objects.filter(part__part=p)
    for ln in lines:
        print(f"   POLine {ln.order.reference} qty={ln.quantity} "
              f"price={ln.purchase_price} recv={ln.received}")
    if not lines:
        print("   POLine: none")
