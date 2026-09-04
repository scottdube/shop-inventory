"""The three duplicated IC pairs: what each record actually holds.

Merging is only trivial when one side is empty. Print stock, suppliers, image
and keywords for each so the choice of survivor is made on evidence.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402
from stock.models import StockItem  # noqa: E402
from order.models import PurchaseOrderLineItem  # noqa: E402

PAIRS = [("NE555", 16, 796), ("ADUM1201", 18, 191), ("PC817", 17, 299)]

for label, a, b in PAIRS:
    print("=" * 72)
    print(label)
    for pk in (a, b):
        try:
            p = Part.objects.get(pk=pk)
        except Part.DoesNotExist:
            print(f"  #{pk}  <gone>")
            continue
        items = StockItem.objects.filter(part=p)
        total = sum(i.quantity for i in items)
        sps = list(p.supplier_parts.all())
        print(f"  #{p.pk}  active={p.active}  {p.name[:58]}")
        print(f"        cat={p.category.pathstring if p.category else None}  IPN={p.IPN!r}")
        print(f"        stock rows={items.count()} total={total}")
        for i in items:
            print(f"           row {i.pk}: qty={i.quantity} loc={i.location}")
        print(f"        suppliers={[(s.supplier.name, s.SKU) for s in sps]}")
        print(f"        image={bool(p.image)}  keywords={bool(p.keywords)}")
        # get_used_in() returns a LIST, not a queryset — .count() is list.count(x).
        # PO lines point at the SupplierPart, not the Part; there is no
        # Part.purchase_order_line_items reverse accessor.
        po_lines = PurchaseOrderLineItem.objects.filter(part__part=p).count()
        print(f"        used_in_bom={len(p.get_used_in())}  po_lines={po_lines}")
