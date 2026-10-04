"""Read-only: PO-0184 and free-looking Bin Wall bins, 2026-10-04.

A bin with 0 stock rows is UNRECORDED, not empty -- this lists candidates for
Scott to confirm, it does not pick one.
"""
import os, sys, django
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings"); django.setup()
from order.models import PurchaseOrder
from stock.models import StockItem, StockLocation
po = PurchaseOrder.objects.get(reference="PO-0184")
print(po.reference, "status", po.status, po.supplier.name, po.supplier_reference, "|", po.description)
for l in po.lines.all():
    sp = l.part; p = sp.part
    print(f"  line {l.pk} {sp.SKU} qty {float(l.quantity)} recv {float(l.received)} pack {sp.pack_quantity}/{sp.pack_quantity_native} {l.purchase_price}"
          f"\n    part #{p.pk} {p.name!r} cat={p.category.pathstring if p.category else None} default={p.default_location.pathstring if p.default_location else None}")
    for s in StockItem.objects.filter(part=p):
        print(f"     SI #{s.pk} qty {s.quantity} @ {s.location.pathstring} meta={s.metadata}")
    # where do siblings in the same category live?
    sib = StockItem.objects.filter(part__category=p.category).exclude(part=p).values_list("location__pathstring", flat=True)
    from collections import Counter
    print("    same-category stock lives at:", Counter(sib).most_common(8))
wall = StockLocation.objects.get(name="Bin Wall")
print("\nBin Wall cabinets:", [(c.name, (c.description or "")[:60]) for c in wall.get_children()])
free = []
for b in wall.get_descendants().filter(children__isnull=True):
    n = StockItem.objects.filter(location=b).count()
    d = (b.description or "")
    if n == 0 or "FREE" in d.upper() or "EMPTY" in d.upper():
        free.append((b.pathstring, n, d[:70], (b.metadata or {}).get("labeled")))
print(f"\n{len(free)} bins with 0 rows or FREE/EMPTY in description:")
for f in sorted(free): print("  ", f)
