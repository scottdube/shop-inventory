"""Stamp #87 as counted, and record the policy that says why it may be stamped.

Scott, 2026-08-24: *"It's now a count. I physically counted it. Seems like
that's implied when you received something and say they're all there and you're
putting them away."*

Correct, and the distinction is narrower than it first sounds -- it does NOT
retract the SHT31 rule, it sharpens it:

    RECEIVING A PO             is not a count and not a location. It is a
                               statement that an order arrived, written by
                               whoever closed the order, often from an email.
    A PERSON PUTTING IT AWAY   IS a count. They had the thing in their hands,
                               they saw how many there were, and they chose the
                               drawer. All three facts are observations.

The SHT31 failure was the first masquerading as the second: two sensors recorded
into a drawer nobody had carried them to. The fix was never "put-aways are
untrustworthy" -- it was "do not let a receipt impersonate one".

So the rule going forward: **a put-away performed by a person, who confirms the
contents, carries a stocktake_date.** A receipt alone never does.

    itq run scripts/putaway_is_a_count.py
    itq run scripts/putaway_is_a_count.py --commit
"""
import argparse
import datetime
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockItem      # noqa: E402

TODAY = datetime.date(2026, 8, 24)
NOTE = ("Hand-counted 2026-08-24 by Scott while filing it into A3-R1C2 — one "
        "nozzle, confirmed in hand, not a figure carried in from the purchase "
        "record. A put-away done by a person who confirms the contents is a "
        "count; a PO receipt on its own is not.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

si = StockItem.objects.get(pk=659)
print(f"stock #{si.pk}  part #{si.part.pk} {si.part.name[:50]}")
print(f"  qty            {float(si.quantity):g}")
print(f"  location       {si.location.pathstring}")
print(f"  stocktake_date {si.stocktake_date}  ->  {TODAY}")
print(f"  notes          {' '.join((si.notes or '').split())[:90]}...")

if not a.commit:
    print("\nDRY RUN — add --commit")
    raise SystemExit

StockItem.objects.filter(pk=si.pk).update(stocktake_date=TODAY, notes=NOTE)
fresh = StockItem.objects.get(pk=si.pk)
assert fresh.stocktake_date == TODAY, f"date did not stick: {fresh.stocktake_date}"
assert fresh.notes == NOTE, "notes did not stick"
print(f"\nOK  stock #{fresh.pk} stocktake_date={fresh.stocktake_date}")
print(f"    {' '.join(fresh.notes.split())[:100]}...")
