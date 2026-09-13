#!/usr/bin/env python3
"""Remove cabinet-level [ESTIMATE] rows that double-count filed stock.

Generalised from scripts/fix_m4_double_count.py, which did the six M4 rows on
2026-09-13. Scott then asked for the two survivors, so this finds the pattern
itself instead of carrying another hand-typed list of primary keys -- a list
that would be wrong the moment anyone files another drawer.

THE PATTERN. A part has a row at a CABINET root (SLN/Bin Wall/B1 and friends)
whose notes start "[ESTIMATE]" and whose quantity is the PURCHASED figure,
plus one or more rows in actual drawers holding hand counts of that same
material after it was filed. Summing them counts one bag twice.

THE PRECONDITION, which is what makes this safe to automate: the rows must sum
to MORE than the part has EVER been received. That is arithmetic, not
judgement -- a shop cannot hold 190 of something it bought 100 of. Any pair
failing that test is left alone and reported, because two rows can legitimately
mean two piles.

Not a merge: InvenTree's merge_stock_items ADDS quantities, baking the error in
permanently. The hand count is already correct; the estimate row describes
nothing that exists. Nothing is invented and no quantity is adjusted.

    itq run scripts/fix_cabinet_double_count.py
    itq run scripts/fix_cabinet_double_count.py --commit
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from order.models import PurchaseOrderLineItem  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
STALE = ("The same part is also filed in 1 other row(s); this row is what is "
         "HERE, not the total. Sum the rows for the shop figure.")

roots = StockLocation.objects.filter(parent__name="Bin Wall")
acted = skipped = 0

for cab in StockItem.objects.filter(location__in=roots).select_related("part", "location"):
    others = list(StockItem.objects.filter(part=cab.part).exclude(pk=cab.pk)
                  .select_related("location"))
    if not others:
        continue

    recv = sum(float(l.received) for l in PurchaseOrderLineItem.objects.filter(
        part__in=SupplierPart.objects.filter(part=cab.part)))
    total = float(cab.quantity) + sum(float(o.quantity) for o in others)

    print(f"\n[{cab.part.pk}] {cab.part.name[:66]}")
    print(f"   cabinet row {cab.pk}: {float(cab.quantity):g} @ {cab.location.pathstring}")
    for o in others:
        print(f"   drawer  row {o.pk}: {float(o.quantity):g} @ "
              f"{o.location.pathstring if o.location else 'NO LOCATION'}")
    print(f"   ever received {recv:g}; rows sum to {total:g}")

    if not (recv and total > recv):
        print("   -> sum does NOT exceed ever-received: two real piles, LEFT ALONE")
        skipped += 1
        continue
    if not (cab.notes or "").startswith("[ESTIMATE]"):
        print("   -> cabinet row is not an [ESTIMATE]: LEFT ALONE, needs a human")
        skipped += 1
        continue
    if len(others) != 1:
        print(f"   -> {len(others)} drawer rows, not 1: LEFT ALONE, needs a human")
        skipped += 1
        continue

    drw = others[0]
    print(f"   -> REMOVE row {cab.pk}; shop figure becomes {float(drw.quantity):g}")
    if not COMMIT:
        continue

    prov = (f"\n\nMERGED 2026-09-13: a second row for this part at cabinet level "
            f"({cab.location.pathstring}, stock {cab.pk}, qty "
            f"{float(cab.quantity):g}) was an [ESTIMATE] seeded from the PURCHASE, "
            f"describing this same material before it was filed into this drawer. "
            f"Summing the two claimed {total:g} against {recv:g} ever received, so "
            f"it was removed. This hand count is the shop figure. Purchase "
            f"provenance is on the purchase order, not lost.")
    StockItem.objects.filter(pk=drw.pk).update(
        notes=(drw.notes or "").replace(STALE, "").rstrip() + prov)
    cab.delete()
    acted += 1

if not COMMIT:
    print(f"\nDRY RUN — would remove {acted if COMMIT else sum(1 for _ in [])} ...")
    print("Re-run with --commit.")
    sys.exit(0)

print(f"\nremoved {acted} estimate row(s); {skipped} left for a human")

print("\n--- verification: any cabinet-level row still over-counting? ---")
bad = 0
for cab in StockItem.objects.filter(location__in=roots).select_related("part", "location"):
    others = StockItem.objects.filter(part=cab.part).exclude(pk=cab.pk)
    if not others:
        continue
    recv = sum(float(l.received) for l in PurchaseOrderLineItem.objects.filter(
        part__in=SupplierPart.objects.filter(part=cab.part)))
    total = float(cab.quantity) + sum(float(o.quantity) for o in others)
    if recv and total > recv:
        bad += 1
        print(f"  [{cab.part.pk}] STILL OVER: {total:g} vs {recv:g} received")
print("PASS — no cabinet-level row over-counts" if bad == 0 else f"FAILED — {bad}")
