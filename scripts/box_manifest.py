"""Put every row in a Florida box on its TransferOrder, so the box has its
manifest ("the box is the thing, the TO is the manifest"). Generalised from
fl01_manifest_1010.py.   itq run scripts/box_manifest.py FL-02 TO-0002
One line per PART (two rows of the same part sum), one allocation per row.
Re-runnable: get_or_create throughout; quantities are set, not added."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from collections import defaultdict
from stock.models import StockItem, StockLocation
from order.models import TransferOrder, TransferOrderLineItem, TransferOrderAllocation
BOX, REF = sys.argv[1], sys.argv[2]
box = StockLocation.objects.get(name=BOX, parent__name="Florida Staging")
to = TransferOrder.objects.get(reference=REF)
rows = list(StockItem.objects.filter(location=box).select_related("part"))
byp = defaultdict(list)
for r in rows: byp[r.part].append(r)
nl = na = 0
for part, rs in byp.items():
    q = sum(float(r.quantity) for r in rs)
    line, c = TransferOrderLineItem.objects.get_or_create(order=to, part=part, defaults={"quantity": q})
    if float(line.quantity) != q:
        TransferOrderLineItem.objects.filter(pk=line.pk).update(quantity=q)
    nl += c
    for r in rs:
        a, c2 = TransferOrderAllocation.objects.get_or_create(line=line, item=r, defaults={"quantity": r.quantity})
        if float(a.quantity) != float(r.quantity):
            TransferOrderAllocation.objects.filter(pk=a.pk).update(quantity=r.quantity)
        na += c2
to.refresh_from_db()
stale = [l for l in to.lines.all() if l.part not in byp]
print(f"{to.reference}: {to.lines.count()} lines ({nl} new), allocations added {na}; "
      f"lines not in {BOX}: {[(l.pk, l.part.name[:40], float(l.quantity)) for l in stale]}")
tot = sum(float(a.quantity) for l in to.lines.all() for a in l.allocations.all())
print(f"allocated pieces {tot:g} vs {BOX} pieces {sum(float(r.quantity) for r in rows):g}")
