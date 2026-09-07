#!/usr/bin/env python3
"""Record a physical count on a stock row, without leaving a contradiction.

Written 2026-09-07 after making the same mistake twice in two days.

Counting an imported row means THREE writes, and doing two of them is worse
than doing none:

    quantity        <- what was counted
    stocktake_date  <- proof somebody counted
    [ESTIMATE]      <- must be REMOVED

The McMaster and Amazon importers open a row's notes with an [ESTIMATE] block
saying "quantity is what was PURCHASED, not a count... no stocktake date on
purpose". Set a date and leave that paragraph and the row now asserts both
"never counted" and "counted on this date". The dashboard flags it as ROW
CONTRADICTS ITSELF, correctly.

**Which half is stale is decided by ONE question: did a human actually count
it?** If yes the marker goes and the date stays, which is this script. If no —
somebody stamped a date without counting — then the DATE goes and the marker
stays, which is the opposite fix and is NOT what this does. Both cases have
happened here; see docs/TRAPS.md.

    itq run scripts/record_count.py 546 92
    itq run scripts/record_count.py 546 92 --note "bagged separately, recount is pick-up-bag"
"""
import argparse
import datetime
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockItem  # noqa: E402

MARK = "[ESTIMATE]"

ap = argparse.ArgumentParser()
ap.add_argument("stock_pk", type=int)
ap.add_argument("quantity", type=float)
ap.add_argument("--note", default="", help="anything worth recording about the count")
ap.add_argument("--date", default=None, help="count date, default today")
a = ap.parse_args()

si = StockItem.objects.get(pk=a.stock_pk)
when = datetime.date.fromisoformat(a.date) if a.date else datetime.date.today()
before = float(si.quantity)

# Keep every paragraph EXCEPT the importer's estimate boilerplate. The rest is
# real history - provenance, prices, earlier corrections - and deleting it to
# clear a marker would trade one wrong record for a poorer one.
kept = [p for p in (si.notes or "").split("\n\n") if not p.strip().startswith(MARK)]
had_marker = len(kept) != len((si.notes or "").split("\n\n"))

head = (f"COUNTED {when}: {a.quantity:g}"
        + (f", was {before:g} on record" if before != a.quantity else "")
        + ". A real count.")
if had_marker:
    head += (f"\n\nThe {MARK} marker was REMOVED because somebody counted this. A "
             f"counted figure carries a stocktake date and a reasoned guess does not; "
             f"both together is the contradiction the dashboard flags.")
if a.note:
    head += f"\n\n{a.note}"

si.quantity = a.quantity
si.stocktake_date = when
si.notes = "\n\n".join([head] + kept)
si.save()
si.refresh_from_db()

assert float(si.quantity) == a.quantity, "quantity did not stick"
assert si.stocktake_date == when, "stocktake date did not stick"
assert not si.notes.startswith(MARK), "marker still leading the notes"
print(f"#{si.pk} {si.part.name[:48]}")
print(f"  {before:g} -> {float(si.quantity):g}   stocktake {si.stocktake_date}"
      f"   marker {'removed' if had_marker else 'was not present'}")

left = StockItem.objects.filter(notes__startswith=MARK,
                                stocktake_date__isnull=False).count()
print(f"  self-contradicting rows in the whole install: {left}")
