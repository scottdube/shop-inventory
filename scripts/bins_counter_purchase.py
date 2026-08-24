"""Attribute the delivered bins to PO-0141, and add the hand-carried 10.

Two lots, kept as two stock rows on purpose. They cost differently-evidenced
money and one of them has no digital trace at all; merging them into a single
quantity would destroy the only thing that distinguishes them.

  lot 1  the DELIVERY, PO-0141, $10.98 verbatim off the Walmart order page.
         Already stocked (row 667) but the note never named the PO, so the
         order sat Placed with the goods on the shelf.

  lot 2  HAND CARRIED from the store, because the delivery was late. No email,
         no portal entry, no order record — invisible to the vendor sweep
         forever. Not a purchase order: a PO asserts an order existed, and this
         catalogue has already been burned by POs that were really inferences
         (the 23 stubs, and the SHT31 rows minted by receiving one).

`[COUNTER PURCHASE]` opens the note so one query finds every such row, the same
way `[ESTIMATE]` works. Without a marker these look like orphan stock to any
future reconciliation.

Price on lot 2 is Scott's recollection that it matched the online price. NOT
verified against a receipt, and said so on the row. The +40% estimate rule is
deliberately NOT applied — that rule exists to stop under-budgeting a FUTURE
purchase, and inflating money already spent would be a different lie.
"""
import argparse, datetime, os, sys
from decimal import Decimal
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from djmoney.money import Money                       # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from order.status_codes import PurchaseOrderStatus     # noqa: E402
from part.models import Part                           # noqa: E402
from stock.models import StockItem, StockLocation      # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

po = PurchaseOrder.objects.get(reference="PO-0141")
line = po.lines.first()
part = Part.objects.get(pk=1089)
row1 = StockItem.objects.get(pk=667)
loc = row1.location

NOTE1 = ("Walmart DELIVERY, received against PO-0141 (ordered 2026-08-22, "
         "$10.98 for the 10-pack). Arrived and confirmed on hand by Scott "
         "2026-08-24; counted 10 unopened, now 9 with B-01 in service. As each "
         "bin goes into service it becomes a LOCATION, not stock — decrement "
         "this row when one is put to work.")
NOTE2 = ("[COUNTER PURCHASE] 10 bins bought IN STORE at Walmart 2026-08-24, "
         "hand carried. The delivery (PO-0141) was late so Scott bought a set "
         "at the counter, then kept the delivery as well. NO order record "
         "exists — no email, no portal entry — so this lot will never appear in "
         "any vendor sweep and is not an orphan. Deliberately NOT given a "
         "purchase order: a PO asserts an order existed and none did. Price "
         "$10.98 is Scott's recollection that it matched the online price and "
         "is NOT verified against a receipt.")

print(f"PO-0141 status={po.get_status_display()} line qty={float(line.quantity):g} "
      f"received={float(line.received):g} price={line.purchase_price}")
print(f"row #{row1.pk} qty={float(row1.quantity):g} @ {loc.pathstring}")
print(f"-> receive PO-0141, re-note row {row1.pk}, add a second row of 10")
if not a.commit:
    print("\nDRY RUN"); raise SystemExit

PurchaseOrderLineItem.objects.filter(pk=line.pk).update(received=line.quantity)
assert float(PurchaseOrderLineItem.objects.get(pk=line.pk).received) == float(line.quantity)
PurchaseOrder.objects.filter(pk=po.pk).update(status=PurchaseOrderStatus.COMPLETE.value)
assert PurchaseOrder.objects.get(pk=po.pk).get_status_display() == "Complete"
print("\nOK  PO-0141 received and Complete")

StockItem.objects.filter(pk=row1.pk).update(notes=NOTE1,
                                            purchase_price=Money(Decimal("10.98"), "USD"))
assert StockItem.objects.get(pk=row1.pk).notes == NOTE1
print(f"OK  row #{row1.pk} re-noted and priced")

si = StockItem.objects.create(
    part=part, location=loc, quantity=10,
    purchase_price=Money(Decimal("10.98"), "USD"),
    stocktake_date=datetime.date(2026, 8, 24), notes=NOTE2)
c = StockItem.objects.get(pk=si.pk)
assert float(c.quantity) == 10 and c.notes.startswith("[COUNTER PURCHASE]")
print(f"OK  row #{c.pk} qty=10 [COUNTER PURCHASE]")
print(f"\ntotal bins on hand: {sum(float(x.quantity) for x in part.stock_items.all()):g} "
      f"(+1 in service as B-01 = 20 bought)")
