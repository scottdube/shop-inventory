"""How many purchases did the import see but never turn into anything findable?

Scott, 2026-08-28: "this should have been turned up in the import earlier on.
There's no reason I should have to go search for it."

Read-only. The proxy: a part whose NOTES carry a seeded purchase-history block
was, by definition, seen by the importer. If that part has no SupplierPart, no
PO line, or no stock row, the import saw the money and produced nothing anyone
can find on a shelf.
"""
import os, re, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from company.models import SupplierPart                          # noqa: E402
from order.models import PurchaseOrderLineItem                   # noqa: E402
from part.models import Part                                     # noqa: E402
from stock.models import StockItem                               # noqa: E402

seen = Part.objects.filter(notes__icontains="Purchase history")
print(f"parts carrying a seeded purchase-history block: {seen.count()}")
print(f"total parts: {Part.objects.count()}\n")

no_sp, no_po, no_stock, ghost = [], [], [], []
for p in seen:
    sp = SupplierPart.objects.filter(part=p).exists()
    po = PurchaseOrderLineItem.objects.filter(part__part=p).exists()
    st = StockItem.objects.filter(part=p).exists()
    if not sp: no_sp.append(p)
    if not po: no_po.append(p)
    if not st: no_stock.append(p)
    if not sp and not po and not st: ghost.append(p)

n = seen.count()
def pct(x): return f"{100*len(x)/n:.0f}%" if n else "-"
print(f"  no SupplierPart : {len(no_sp):>4}  {pct(no_sp)}   nothing links it to a vendor")
print(f"  no PO line      : {len(no_po):>4}  {pct(no_po)}   the money never became an order")
print(f"  no stock row    : {len(no_stock):>4}  {pct(no_stock)}   bought, never recorded on hand")
print(f"  ALL THREE       : {len(ghost):>4}  {pct(ghost)}   invisible unless a box turns up\n")

print("the 20 most expensive ghosts — bought, no vendor link, no order, no stock:")
def spend(p):
    m = re.search(r"\*\*([\d,]+) purchases?, ([\d,]+) units? lifetime, \$([\d,.]+) total\*\*",
                  p.notes or "")
    return float(m.group(3).replace(",", "")) if m else 0.0
for p in sorted(ghost, key=spend, reverse=True)[:20]:
    print(f"  ${spend(p):>9,.2f}  #{p.pk:<5} {p.name[:56]}")
print(f"\ntotal lifetime spend sitting in ghost rows: ${sum(spend(p) for p in ghost):,.2f}")
