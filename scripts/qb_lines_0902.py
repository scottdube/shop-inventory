"""What do PO-0025/0026/0027 actually carry, line by line?

The survey found the three orders queue B calls "not imported" already exist as
completed POs. That does not by itself mean the COST was captured: a PO can be
imported with null purchase_price on every line, which is exactly the state
queue B exists to fix. So measure the lines, the supplier-part price breaks and
the stock rows, and say which of the three is genuinely done.

Read-only.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from stock.models import StockItem  # noqa: E402

for ref in ["PO-0025", "PO-0026", "PO-0027"]:
    po = PurchaseOrder.objects.filter(reference=ref).first()
    if not po:
        print(f"{ref}: MISSING")
        continue
    print(f"\n=== {ref}  supplier_ref={po.supplier_reference!r}  {po.get_status_display()}  "
          f"supplier={po.supplier}  issue={po.issue_date} complete={po.complete_date} ===")
    for ln in po.lines.all().order_by("pk"):
        sp = ln.part
        sku = sp.SKU if sp else "?"
        part = sp.part if sp else None
        print(f"  line {ln.pk:4d} sku={sku:10s} qty={ln.quantity} recv={ln.received} "
              f"price={ln.purchase_price} part={part.pk if part else None}")

print("\n=== supplier part price breaks + stock cost for the 11 candidates ===")
SKUS = ["51240", "51208", "31280", "37237", "39676", "37553",
        "39670", "39668", "39671", "39673", "00447474"]
for sku in SKUS:
    sp = SupplierPart.objects.filter(SKU=sku).first()
    if not sp:
        print(f"  {sku}: no supplier part")
        continue
    breaks = list(sp.pricebreaks.all())
    items = StockItem.objects.filter(supplier_part=sp)
    stock_costs = [(si.pk, si.quantity, si.purchase_price) for si in items]
    print(f"  {sku:10s} sp={sp.pk:4d} part={sp.part.pk:4d} breaks={len(breaks)} "
          f"{[(str(b.quantity), str(b.price)) for b in breaks]} stock={stock_costs}")

print("\n=== do the parts have any pricing at all? ===")
for sku in SKUS:
    sp = SupplierPart.objects.filter(SKU=sku).first()
    if not sp:
        continue
    p = sp.part
    pricing = getattr(p, "pricing", None)
    print(f"  {sku:10s} part={p.pk:4d} {p.name[:40]:40s} "
          f"purchase_min={getattr(pricing, 'purchase_cost_min', None)} "
          f"purchase_max={getattr(pricing, 'purchase_cost_max', None)} "
          f"supplier_min={getattr(pricing, 'supplier_price_min', None)}")
