#!/usr/bin/env python3
"""Return events from the Amazon mail -> InvenTree. Called by the
amazon-refund-watch task; also usable by hand.

    itq run scripts/returns.py requested --order 113-8469851-5845865 [--reason "wrong size"]
    itq run scripts/returns.py dropoff   --order 113-8469851-5845865
    itq run scripts/returns.py refunded  --order 113-8469851-5845865 --amount 6.99 --date 2026-11-09 --commit

Dry run by default: prints the result it WOULD produce and rolls back.
Exit 0 ok, 2 pending (a [NEEDS-DECISION] question was written), 1 error -
but `itq run` swallows the remote exit code (its output goes through
`grep -Ev ... || true`), so a caller reads the JSON "action" field, not $?.
"""
import argparse, datetime, json, os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db import transaction  # noqa: E402
from plugins.receiving import returns as R  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("event", choices=["requested", "dropoff", "refunded"])
ap.add_argument("--order", required=True)
ap.add_argument("--amount", type=float, default=None)
ap.add_argument("--date", default=str(datetime.date.today()))
ap.add_argument("--reason", default="")
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()


class DryRun(Exception):
    pass


try:
    with transaction.atomic():
        if a.event == "refunded":
            if a.amount is None:
                sys.exit("refunded needs --amount")
            res = R.refunded(a.order, a.amount, a.date)
        else:
            res = R.requested(a.order, a.date, reason=a.reason, event=a.event)
        if not a.commit:
            raise DryRun()
except DryRun:
    print("DRY RUN — rolled back. Re-run with --commit.")

print(json.dumps(res, indent=1))
if res.get("push"):
    print("PUSH:", res["push"])
sys.exit(0 if res["ok"] else (2 if res.get("pending") else 1))
