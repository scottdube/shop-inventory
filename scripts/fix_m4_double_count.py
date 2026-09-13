#!/usr/bin/env python3
"""Remove the six cabinet-level M4 rows that double-count filed stock.

Scott, 2026-09-13, after asking whether the shop had M4 x 30: "fix the double
counted M4 rows."

WHAT WAS WRONG. Each M4 screw part carried TWO rows:

  * one at SLN/Bin Wall/B1 -- the CABINET, not a drawer -- whose notes say
    "[ESTIMATE] Quantity is what was PURCHASED ... not a count"
  * one in the actual drawer, hand-counted by Scott on 2026-09-06

They are the SAME MATERIAL. The estimate was seeded from the purchase; the
count was taken after that material was filed into a drawer. Summing them
counts one bag twice.

HOW THAT WAS ESTABLISHED, rather than assumed. Each part has exactly ONE
purchase order, one pack, fully received -- and in every case the two rows sum
to MORE than was ever received. #995: 100 received, rows sum to 190. That is
not a judgement call about filing habits, it is arithmetic: the shop cannot
hold 190 of something it bought 100 of and has been drawing from since 2023.

#993 settles the mechanism beyond doubt. Its drawer note reads: "COUNTED 80 by
Scott 2026-09-06 ... the bag reads M4X6 QTY 100." One bag, labelled 100,
containing 80. Not two bags.

NOT A MERGE. InvenTree's merge_stock_items ADDS quantities, which would write
190 into a single row and make the error permanent and invisible. The counted
row is correct as it stands; the estimate row describes nothing that exists.

The hand count always wins over the purchase estimate -- that is the evidence
tier order, and it is why nothing here invents a number. No quantity is
adjusted anywhere: six rows that represent no physical object are removed.

    itq run scripts/fix_m4_double_count.py
    itq run scripts/fix_m4_double_count.py --commit
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from order.models import PurchaseOrderLineItem  # noqa: E402
from stock.models import StockItem  # noqa: E402

COMMIT = "--commit" in sys.argv

# (cabinet row to remove, drawer row that survives)
PAIRS = [(496, 777), (497, 778), (476, 781), (475, 780), (494, 782), (489, 783)]

STALE = ("The same part is also filed in 1 other row(s); this row is what is "
         "HERE, not the total. Sum the rows for the shop figure.")

removed = kept = 0
for cab_pk, drw_pk in PAIRS:
    cab = StockItem.objects.filter(pk=cab_pk).select_related('part', 'location').first()
    drw = StockItem.objects.filter(pk=drw_pk).select_related('part', 'location').first()
    if cab is None:
        print(f"  row {cab_pk} already gone — skipping")
        continue
    assert cab.part_id == drw.part_id, f"{cab_pk}/{drw_pk} are different parts"
    assert cab.location.name == 'B1', f"{cab_pk} is not a cabinet-level row"

    recv = sum(float(l.received) for l in PurchaseOrderLineItem.objects.filter(
        part__in=SupplierPart.objects.filter(part_id=cab.part_id)))
    total = float(cab.quantity) + float(drw.quantity)

    print(f"\n[{cab.part.pk}] {cab.part.name[:66]}")
    print(f"   REMOVE row {cab.pk}: {float(cab.quantity):g} @ {cab.location.pathstring} [ESTIMATE]")
    print(f"   KEEP   row {drw.pk}: {float(drw.quantity):g} @ {drw.location.pathstring} (hand count)")
    print(f"   ever received {recv:g}; rows summed to {total:g}; shop figure becomes {float(drw.quantity):g}")

    # Guard: only remove when the arithmetic actually proves the duplication.
    if not (recv and total > recv):
        print("   !! sum does NOT exceed ever-received — NOT SAFE, skipping")
        continue

    if not COMMIT:
        continue

    prov = (f"\n\nMERGED 2026-09-13: a second row for this part at cabinet level "
            f"(SLN/Bin Wall/B1, stock {cab.pk}, qty {float(cab.quantity):g}) was an "
            f"[ESTIMATE] seeded from the PURCHASE, describing this same material "
            f"before it was filed into this drawer. Summing the two claimed "
            f"{total:g} against {recv:g} ever received, so it was removed. This "
            f"hand count is the shop figure. Purchase provenance is on the "
            f"purchase order, not lost.")
    note = (drw.notes or "").replace(STALE, "").rstrip() + prov
    StockItem.objects.filter(pk=drw.pk).update(notes=note)

    cab.delete()
    removed += 1
    kept += 1

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

print(f"\nremoved {removed} estimate row(s); {kept} hand count(s) left standing")

print("\n--- verification ---")
bad = 0
for _, drw_pk in PAIRS:
    d = StockItem.objects.filter(pk=drw_pk).select_related('part').first()
    n = StockItem.objects.filter(part=d.part).count()
    recv = sum(float(l.received) for l in PurchaseOrderLineItem.objects.filter(
        part__in=SupplierPart.objects.filter(part=d.part)))
    tot = sum(float(s.quantity) for s in StockItem.objects.filter(part=d.part))
    ok = n == 1 and tot <= recv
    bad += 0 if ok else 1
    print(f"  [{d.part.pk}] rows={n}  on hand={tot:g}  received={recv:g}  "
          f"{'OK' if ok else 'STILL WRONG'}")
    if STALE in (d.notes or ""):
        print("     !! stale 'sum the rows' instruction still present")
        bad += 1
print(("PASS" if bad == 0 else f"FAILED — {bad} problem(s)"))
