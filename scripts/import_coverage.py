#!/usr/bin/env python3
"""How far back the purchase history reaches — as POs, and as PARTS.

Written 2026-09-01, then immediately corrected, and the correction is the point.

A #35 roller chain was catalogued "NO PURCHASE RECORD". Scott found it on Amazon
in seconds: B083JVS632, 2022-02-07. The first explanation offered was that the
Amazon import only reaches 2025-07-22 — thirteen months — so the chain simply
predated it.

**That was wrong, and Scott said so: "we definitely would go further back than
thirteen months in Amazon."** He was right. The Amazon import reaches back to
2012. What reaches back thirteen months is PURCHASE ORDER CREATION. The importer
made PARTS for old orders and POs only for recent ones:

    Amazon PurchaseOrders   earliest 2025-07-22    13 months
    Amazon-sourced PARTS    earliest 2012-03-01    14 years
    Amazon parts dated 2022                        70 of them

So the chain is a SELECTIVE MISS, not a coverage boundary. The era is well
covered and this one item is absent. Why is not established — a plausible but
UNVERIFIED guess is that the importer filtered by Amazon department and a
motorcycle chain sits under Automotive rather than Industrial & Scientific.

The lesson is the one being repeated all week, now at a third level. Measuring
PurchaseOrder.issue_date and saying "the import is 13 months deep" claims more
than the query saw: it was a fact about the PO table stated as a fact about the
import. Same error as "no M2 screws" (true of the database, false of the shop)
and "unfiled = 2" (true of locations, false of stock) — and this time it was
made in the very commit that wrote those up.

So this script reports BOTH floors, because either one alone misleads.

    itq run scripts/import_coverage.py
    itq run scripts/import_coverage.py --before 2022-02-07
"""
import argparse
import datetime
import os
import sys
from collections import defaultdict

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--before", help="a date (YYYY-MM-DD); flags suppliers whose import "
                                 "does not reach it")
a = ap.parse_args()

by_sup = defaultdict(list)
for po in PurchaseOrder.objects.exclude(issue_date__isnull=True):
    by_sup[po.supplier.name if po.supplier else "(no supplier)"].append(po.issue_date)

print("IMPORTED PURCHASE HISTORY — how far back each supplier actually reaches\n")
print(f"{'supplier':34} {'POs':>4}  {'earliest':>11}  {'latest':>11}   span")
for sup, dates in sorted(by_sup.items(), key=lambda kv: -len(kv[1])):
    lo, hi = min(dates), max(dates)
    print(f"{sup[:34]:34} {len(dates):>4}  {lo!s:>11}  {hi!s:>11}   "
          f"{(hi - lo).days // 30} months")

# The PO floor alone is misleading: parts were imported for orders that never
# got a PO, so a supplier can look 13 months deep and be 14 years deep.
import re as _re  # noqa: E402
from company.models import SupplierPart  # noqa: E402

_date = _re.compile(r"(20[0-2]\d-\d{2}-\d{2})")
part_floor = {}
for sp in SupplierPart.objects.select_related("part", "supplier"):
    if not sp.part or not sp.supplier:
        continue
    hay = f"{sp.part.description or ''} {sp.part.notes or ''}"
    ds = _date.findall(hay)
    if ds:
        lo = min(ds)
        k = sp.supplier.name
        if k not in part_floor or lo < part_floor[k]:
            part_floor[k] = lo

print("\nPART-DERIVED floor — dates found in part records, including orders that "
      "\nnever became a PO. THIS is how far the import actually reached:\n")
for sup in sorted(set(list(by_sup) + list(part_floor))):
    po_lo = min(by_sup[sup]) if by_sup.get(sup) else None
    pt_lo = part_floor.get(sup)
    gap = ""
    if po_lo and pt_lo and str(pt_lo) < str(po_lo):
        gap = "   <-- parts predate the first PO by years"
    print(f"  {sup[:32]:32} PO {str(po_lo or '-'):>10}   parts {str(pt_lo or '-'):>10}{gap}")

print("\nNeither floor is a start date. A part ABSENT from a well-covered era is a "
      "\nMISS, not a boundary — check the vendor's own order history before "
      "\nconcluding anything about how the item arrived.")

if a.before:
    want = datetime.date.fromisoformat(a.before)
    print(f"\nAgainst {want}:")
    blind = [(s, min(d)) for s, d in by_sup.items() if min(d) > want]
    for s, lo in sorted(blind, key=lambda r: r[1]):
        print(f"  !! {s[:36]:36} import starts {lo} — BLIND to {want}")
    if not blind:
        print("  OK  every supplier's import reaches that far back.")
    sys.exit(1 if blind else 0)
