"""Backfill PO + supplier part on the two rows receive_po.py created unlinked, 2026-10-04.

receive_po.py's new-row branch never set purchase_order/supplier_part (fixed the
same day), so SI 898 (PO-0185) and SI 899 (PO-0186) are invisible on their POs'
received-items tab. Queryset .update() so a silent .save() cannot fake it; re-read.
"""
import os, sys, django
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings"); django.setup()
from order.models import PurchaseOrder
from stock.models import StockItem
for si, ref in ((898, "PO-0185"), (899, "PO-0186")):
    po = PurchaseOrder.objects.get(reference=ref)
    ln = po.lines.get()
    s = StockItem.objects.get(pk=si)
    assert s.part_id == ln.part.part_id, (si, ref)
    StockItem.objects.filter(pk=si).update(purchase_order=po, supplier_part=ln.part)
    s.refresh_from_db()
    print(si, s.part.name[:40], "-> PO", s.purchase_order.reference, "SP", s.supplier_part.SKU, "@", s.location.pathstring)
