"""Undo binscan filings, and reconcile purchased against counted.

Two jobs from one journal. Every `/api/assign` write records the row's full
BEFORE state -- location, quantity, stocktake date and notes -- so a filing can
be reversed exactly, and the purchased/counted difference can be reported
without parsing prose.

    itq run scripts/binscan_undo.py --list
    itq run scripts/binscan_undo.py --reconcile
    itq run scripts/binscan_undo.py --undo <stock-pk> --commit
    itq run scripts/binscan_undo.py --undo-since 2026-08-22T17:00 --commit

**Why a journal rather than InvenTree's own history.** Tracking records the
quantity and location changes, but NOT the notes field, and the notes are where
this catalogue keeps its provenance -- the [ESTIMATE] flag, the purchase date,
why a figure is what it is. Stock 514's original notes were lost on 2026-08-22
because a write happened with nothing capturing them first. This exists so that
cannot recur.

The journal lives at ~/binscan/log.jsonl on the Mini and is NOT in git and NOT
backed up. That is acceptable for an undo log -- it is only useful for as long
as the writes are recent -- but do not treat it as an archive.
"""
import argparse
import json
import os
import pathlib
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockItem, StockLocation      # noqa: E402

LOG = pathlib.Path.home() / "binscan" / "log.jsonl"

ap = argparse.ArgumentParser()
ap.add_argument("--list", action="store_true")
ap.add_argument("--reconcile", action="store_true")
ap.add_argument("--undo", type=int, help="stock pk; undoes its most recent filing")
ap.add_argument("--undo-since", help="ISO timestamp; undoes every filing at or after it")
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

if not LOG.exists():
    sys.exit(f"no journal at {LOG}")

rows = []
for line in LOG.read_text().splitlines():
    try:
        r = json.loads(line)
    except Exception:
        continue
    if r.get("kind") == "assign" and r.get("before"):
        rows.append(r)

if not rows:
    sys.exit("no filings journalled yet — the journal only records writes made "
             "after 2026-08-22, when before-state capture was added")

if a.list or not (a.reconcile or a.undo or a.undo_since):
    print(f"  {len(rows)} filing(s) journalled\n")
    print(f"  {'when':<17} {'stock':>6} {'from':<8} -> {'to':<10} {'qty':>7} {'counted':<8} part")
    # The stock detail endpoint omits location_detail, so the journal records a
    # pk and sometimes no name. Resolve it here rather than storing a name that
    # could go stale if a location is renamed.
    names = {l.pk: l.name for l in StockLocation.objects.all()}
    for r in rows:
        b, af = r["before"], r["after"]
        b["location"] = b.get("location") or names.get(b.get("location_pk"), "?")
        print(f"  {r['at'][:16]:<17} {r['stock']:>6} {str(b['location'])[:8]:<8} -> "
              f"{af['location'][:10]:<10} {af['quantity']:>7g} "
              f"{'yes' if r['counted'] else 'no':<8} {(r.get('part') or '')[:38]}")
    if not a.reconcile:
        raise SystemExit

if a.reconcile:
    counted = [r for r in rows if r["counted"]]
    print(f"\n  RECONCILIATION — {len(counted)} counted filing(s)\n")
    if not counted:
        print("    Nothing counted yet. A filing with a blank count carries the")
        print("    purchased figure forward and is deliberately not reconciled:")
        print("    there is no second number to compare it against.")
        raise SystemExit
    print(f"  {'stock':>6} {'drawer':<10} {'was':>6} {'counted':>8} {'gap':>6}  part")
    gaps = []
    for r in counted:
        was, now = r["before"]["quantity"], r["after"]["quantity"]
        gap = now - was
        if abs(gap) > 1e-9:
            gaps.append((r, gap))
        print(f"  {r['stock']:>6} {r['after']['location']:<10} {was:>6g} {now:>8g} "
              f"{gap:>+6g}  {(r.get('part') or '')[:36]}")
    print(f"\n  {len(gaps)} row(s) differ from what the record held.")
    if gaps:
        print("\n  These are the question to put to Scott — NOT on the phone at the")
        print("  drawer, but afterwards, in a batch, while the shape of the week is")
        print("  still in mind. The purchased figure is a real record of what was")
        print("  BOUGHT; the count is what is THERE. The difference went somewhere.")
        for r, gap in gaps:
            n = abs(gap)
            print(f"    - {(r.get('part') or '')[:52]}")
            print(f"        bought {r['before']['quantity']:g}, counted "
                  f"{r['after']['quantity']:g} — where did {n:g} go?")
        print("\n  Feed answers to scripts/unaccounted.py --answer PART=PROJECT,")
        print("  which writes 'CONSUMED BY:' onto the part and builds the project")
        print("  vocabulary the Project column reads.")
    raise SystemExit

targets = []
if a.undo:
    hits = [r for r in rows if r["stock"] == a.undo]
    if not hits:
        sys.exit(f"stock {a.undo} has no journalled filing")
    targets = [hits[-1]]
if a.undo_since:
    targets = [r for r in rows if r["at"] >= a.undo_since]
    if not targets:
        sys.exit(f"nothing filed at or after {a.undo_since}")

print(f"  undoing {len(targets)} filing(s)\n")
for r in targets:
    b = r["before"]
    s = StockItem.objects.filter(pk=r["stock"]).first()
    if not s:
        print(f"    stock {r['stock']}: GONE, skipping")
        continue
    loc = StockLocation.objects.filter(pk=b["location_pk"]).first()
    print(f"    stock {r['stock']}  {(r.get('part') or '')[:44]}")
    print(f"      location  {s.location.name if s.location else None} -> {loc.name if loc else '?'}")
    print(f"      quantity  {float(s.quantity):g} -> {b['quantity']:g}")
    print(f"      stocktake {s.stocktake_date} -> {b['stocktake_date']}")
    print(f"      notes     restored to the {len(b['notes'])}-char version captured before the write")
    if a.commit:
        StockItem.objects.filter(pk=r["stock"]).update(
            location=loc, quantity=b["quantity"],
            stocktake_date=b["stocktake_date"] or None, notes=b["notes"])
        chk = StockItem.objects.get(pk=r["stock"])
        ok = (chk.location_id == b["location_pk"]
              and abs(float(chk.quantity) - b["quantity"]) < 1e-9
              and (chk.notes or "") == b["notes"])
        print(f"      {'restored and verified' if ok else 'RESTORE DID NOT VERIFY'}")

if not a.commit:
    print("\n  DRY RUN — add --commit")
