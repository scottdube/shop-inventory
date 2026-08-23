"""Restore the four pull-stud rows that zeroing DELETED, 2026-08-23.

`pullstud_reconcile.py` set the Shars (#120) and Tormach (#539) pull studs to
zero, intending the #292 pattern: a zero row that keeps its price, its PO link
and a note saying why it is zero. Instead all four rows vanished.

**Cause:** `StockItem.updateQuantity(0)` DELETES the row when
`delete_on_deplete` is true, and it is true by default here —
`STOCK_DELETE_DEPLETED_DEFAULT = True`. Every row created by a receive or an
import inherits it. So "count it down to zero" and "erase the record that it
ever existed" are the same call.

**And the verify block passed anyway.** It checked

    tot = sum(...) == target        # sum([]) == 0 -> True
    all(stocktake_date set)         # all([]) -> True
    all(notes written)              # all([]) -> True

against an EMPTY queryset, and every one of those is vacuously true. A verify
that cannot tell "correctly zero" from "gone" is not a verify. This one now
asserts the row COUNT first.

Restores all four at quantity 0 with `delete_on_deplete=False`, carrying the
original locations, prices, PO links and the explanatory notes.
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from djmoney.money import Money                # noqa: E402
from order.models import PurchaseOrder         # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

TODAY = "2026-08-23"
UNFILED = "SLN/Machine Shop/Unfiled - Machine Shop"

SPENT = (
    "COUNTED 0 by implication, 2026-08-23. Scott counted the pull studs: 20 total, "
    "two kinds, one 10-pack each — the Haas Standard (#110) and Haas TSC (#113) packs "
    "bought in the last month. These {q} are not among them.\n\n"
    "A pull stud lives screwed into a tool holder. {why} They are installed, not "
    "missing, and this row is the spent history of that purchase — it keeps the price "
    "and the order link and stays at zero.\n\n"
    "NOT independently verified: nobody has unscrewed a holder to look. If a holder "
    "ever turns up bare, this is the row that says where its stud went.\n\n"
    "This row was RECREATED 2026-08-23 after the original was deleted by "
    "delete_on_deplete when it was counted to zero. Same facts, new pk."
)

WHY_SHARS = ("Bought loose from Shars across 2024 and 2025, in the same period the "
             "rack filled up.")
WHY_TORMACH = ("Bought from Tormach in February 2024 on the SAME two orders as the "
               "BT30 holders they screw into: PO-0025 carried 7 holders and 8 studs, "
               "PO-0026 carried 1 arbor and 1 stud. Eight holders, nine studs, bought "
               "together — near 1:1 is what installing them looks like.")

# (part_pk, original_qty, unit_price, po_reference or None, why)
ROWS = [
    (120, 3, "8.35", None, WHY_SHARS),
    (120, 4, "8.35", None, WHY_SHARS),
    (539, 8, "10.95", "PO-0025", WHY_TORMACH),
    (539, 1, "10.95", "PO-0026", WHY_TORMACH),
]

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.filter(pathstring=UNFILED).first()
if not loc:
    sys.exit(f"MISSING LOCATION: {UNFILED}")

for part_pk, qty, price, po_ref, why in ROWS:
    existing = StockItem.objects.filter(part_id=part_pk).count()
    po = PurchaseOrder.objects.filter(reference=po_ref).first() if po_ref else None
    if po_ref and not po:
        sys.exit(f"MISSING PO {po_ref}")
    print(f"\n[{part_pk}] restore a 0-qty row (was {qty}, ${price}, "
          f"po={po_ref or '-'}) — part currently has {existing} row(s)")
    if a.commit:
        si = StockItem(
            part_id=part_pk,
            location=loc,
            quantity=0,
            purchase_order=po,
            purchase_price=Money(price, "USD"),
            delete_on_deplete=False,
            stocktake_date=TODAY,
            notes=SPENT.format(q=f"{qty:g}" if isinstance(qty, float) else str(qty),
                               why=why),
        )
        si.save()
        print(f"    created item {si.pk}")

print("\n" + "=" * 74)
print("VERIFY — row COUNT first, because sum([]) == 0 looks like success")
print("=" * 74)
ok = True
for part_pk, want_rows in ((120, 2), (539, 2)):
    items = list(StockItem.objects.filter(part_id=part_pk))
    tot = sum(float(i.quantity) for i in items)
    dod = [i.delete_on_deplete for i in items]
    dated = [i.stocktake_date for i in items]
    good = (len(items) == want_rows and tot == 0
            and not any(dod) and all(dated))
    ok = ok and good
    print(f"  {'ok ' if good else 'BAD'} [{part_pk}] rows={len(items)} (want {want_rows}) "
          f"total={tot:g} delete_on_deplete={dod} stocktake={dated}")
    for i in items:
        print(f"        item {i.pk}: qty={float(i.quantity):g} "
              f"po={i.purchase_order.reference if i.purchase_order else '-'} "
              f"price={i.purchase_price} @ {i.location.name if i.location else '-'}")
print("\nALL VERIFIED" if ok else "\n*** MISMATCH — investigate ***")
print("\n" + ("WROTE" if a.commit else "DRY RUN — add --commit"))
