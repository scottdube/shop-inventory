import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()

from company.models import SupplierPart
from stock.models import StockItem

print("Supplier parts with pack_quantity != 1, and the stock rows sourced from them:\n")
hits = 0
for sp in SupplierPart.objects.all():
    pq = (sp.pack_quantity or '1').strip()
    try:
        pqv = float(pq)
    except ValueError:
        continue
    if pqv == 1:
        continue
    rows = StockItem.objects.filter(supplier_part=sp)
    if not rows.exists():
        print(f"  {sp.supplier.name:<28} {sp.SKU:<20} pack={pq:<6} -- no stock rows")
        continue
    for r in rows:
        q = float(r.quantity)
        flag = ""
        # A row whose quantity is a whole number of PACKS rather than pieces is
        # the signature of receive_line_item ignoring pack_quantity.
        if q > 0 and q % pqv != 0 and q < pqv:
            flag = "  <== SUSPECT: fewer pieces than one pack"
        print(f"  {sp.supplier.name:<28} {sp.SKU:<20} pack={pq:<6} stock#{r.pk} qty={r.quantity} price={r.purchase_price}{flag}")
        if flag:
            hits += 1
print(f"\nsuspect rows: {hits}")
