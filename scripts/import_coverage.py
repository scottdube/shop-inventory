#!/usr/bin/env python3
"""How far back the imported purchase history actually reaches, per supplier.

Written 2026-09-01 after a #35 roller chain was catalogued with "NO PURCHASE
RECORD — no PO line anywhere mentions roller chain". Scott found it in the
Amazon order history in seconds: bought 2022-02-07, 10 ft, $27.99.

The claim was wrong in a specific and repeatable way. There WAS no PO — and
there could not have been, because the Amazon import only reaches back to
2025-07-22. The chain predates the import by three and a half years.

    Amazon         39 POs   earliest 2025-07-22   <- 13 months
    McMaster-Carr  18 POs   earliest 2021-01-25   <- 5 years

The two importers were written at different times with different reach, and
nothing recorded that. So a part bought from Amazon in 2023 looks identical to
a part never bought at all, and the database cannot tell you which it is.

**Before writing "no purchase record", run this.** If the part predates that
supplier's earliest PO, the honest sentence is "no purchase record IN INVENTREE;
the import does not reach that far", and the next move is the vendor's own order
history, not a shrug.

Same shape as two other traps this shop has paid for:
  - "no M2 screws" was true of the database and false of the shop
  - "location IS NULL" rows were invisible to a lamp that counted locations
Each time the query was correct and the CLAIM was too broad.

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

print("\nThe earliest PO for a supplier is a FLOOR, not a start date. Anything "
      "\nbought before it is invisible here and must be looked up at the vendor.")

if a.before:
    want = datetime.date.fromisoformat(a.before)
    print(f"\nAgainst {want}:")
    blind = [(s, min(d)) for s, d in by_sup.items() if min(d) > want]
    for s, lo in sorted(blind, key=lambda r: r[1]):
        print(f"  !! {s[:36]:36} import starts {lo} — BLIND to {want}")
    if not blind:
        print("  OK  every supplier's import reaches that far back.")
    sys.exit(1 if blind else 0)
