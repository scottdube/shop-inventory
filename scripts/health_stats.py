"""One-shot health metrics, to ground a dashboard brief in real numbers.

Read-only. Every figure here is meant to answer "what do I do next", not
"how big is the pile" — so where a count has an actionable and an
unactionable half, both are printed.
"""
import datetime
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem  # noqa: E402

today = datetime.date.today()
EMPTY_KW = Q(keywords="") | Q(keywords__isnull=True)

print("== CATALOG ==")
tot = Part.objects.count()
act = Part.objects.filter(active=True).count()
print(f"parts total={tot} active={act} inactive={tot-act}")
print(f"no image      : {Part.objects.filter(Q(image='')|Q(image__isnull=True)).count()}")
print(f"no keywords   : {Part.objects.filter(EMPTY_KW).count()}")
print(f"no category   : {Part.objects.filter(category__isnull=True).count()}")
print(f"no supplier   : {Part.objects.filter(supplier_parts__isnull=True).count()}")

print("\n== EXCLUSION / TOMBSTONE MARKERS (should not be re-discovered) ==")
for tag in ("NOT INVENTORY", "MERGED into", "REFUNDED", "POSSIBLE RETURN"):
    print(f"{tag:18}: {Part.objects.filter(description__icontains=tag).count()}")

# [ESTIMATE] lives on StockItem.notes, NOT Part.description. Querying the
# description returned 0 and read as "the +40% convention is dead"; it is very
# much alive. An assertion pointed at the wrong field returns a confident,
# plausible, wrong number - which is the exact failure the health brief exists
# to catch, one level up. Name the field so a zero can be told from a miss.
est = StockItem.objects.filter(notes__icontains="[ESTIMATE]")
print(f"{'[ESTIMATE]':18}: {est.count()}  (StockItem.notes — NOT Part.description, which reads 0)")

# An estimate is BY DEFINITION unstamped: a counted figure carries
# stocktake_date, a reasoned guess does not. Both together is a contradiction.
bad = est.filter(stocktake_date__isnull=False)
print(f"{'  ^ contradictions':18}: {bad.count()}  (marked [ESTIMATE] *and* stocktake-stamped — should be 0)")
for s_ in bad[:10]:
    print(f"      stock #{s_.pk} {str(s_.part)[:44]} qty={s_.quantity} stamped={s_.stocktake_date}")

print("\n== PURCHASE ORDERS ==")
for po in PurchaseOrder.objects.all():
    pass
open_pos = [p for p in PurchaseOrder.objects.all() if p.get_status_display() == "Placed"]
print(f"POs total={PurchaseOrder.objects.count()}  PLACED(open)={len(open_pos)}")
for p in sorted(open_pos, key=lambda x: (x.issue_date or today)):
    age = (today - p.issue_date).days if p.issue_date else None
    n = p.lines.count()
    unpriced = p.lines.filter(purchase_price=None).count()
    print(f"  {p.reference:10s} age={str(age)+'d':>6s} {str(p.supplier)[:22]:22s} "
          f"lines={n} unpriced={unpriced}")

tl = PurchaseOrderLineItem.objects.count()
tu = PurchaseOrderLineItem.objects.filter(purchase_price=None).count()
print(f"PO lines total={tl}  with NO price={tu}")

print("\n== STOCK PROVENANCE ==")
si = StockItem.objects.count()
counted = StockItem.objects.filter(stocktake_date__isnull=False).count()
print(f"stock items={si}  with stocktake_date={counted}  never counted={si-counted}")
parts_with_stock = Part.objects.filter(stock_items__isnull=False).distinct().count()
print(f"parts holding stock={parts_with_stock}  active parts with NO stock={Part.objects.filter(active=True).exclude(stock_items__isnull=False).distinct().count()}")
