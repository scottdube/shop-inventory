"""Read-only probe 2026-10-31: PO-0266..0269 lines, the SLN Akro precedent (PO-0142), LRD bench locations."""
import os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from order.models import PurchaseOrder
from stock.models import StockItem, StockLocation

for ref in ["PO-0142", "PO-0266", "PO-0267", "PO-0268", "PO-0269"]:
    po = PurchaseOrder.objects.get(reference=ref)
    print(f"\n{ref} status={po.status} {po.description[:70]}")
    for ln in po.lines.all():
        p = ln.part.part if ln.part else None
        print(f"  line {ln.pk}: qty={ln.quantity} recv={ln.received} part={p.pk if p else None} {p.name if p else ''} default_loc={p.default_location.pathstring if p and p.default_location else None}")
        if p:
            for s in StockItem.objects.filter(part=p):
                print(f"     stock {s.pk} q={s.quantity} @ {s.location.pathstring if s.location else None} meta={s.metadata}")
            pass
print("\nLRD bench-ish locations:")
for l in StockLocation.objects.filter(name__iregex=r'bench|receiving').order_by('pk'):
    print(f"  {l.pk} {l.pathstring}")
