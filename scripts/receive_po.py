#!/usr/bin/env python3
"""Receive a purchase order from the command line. Same flags as before; the
work is done by plugins/receiving/engine.py, which BinScan's /receive page
also calls. Two doors, one engine - the two halves of a receive were each got
wrong once when there were two code paths.

    itq run scripts/receive_po.py PO-0146 --to RB-14
    itq run scripts/receive_po.py PO-0146 --to RB-14 --commit
"""
import argparse, datetime, os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from order.models import PurchaseOrder  # noqa: E402
from stock.models import StockLocation  # noqa: E402
from plugins.receiving import engine  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("reference")
ap.add_argument("--to", required=True, help="destination StockLocation pk, name or pathstring")
ap.add_argument("--commit", action="store_true")
ap.add_argument("--date", default=None)
ap.add_argument("--part", type=int, action="append", default=None,
                help="receive only lines for this Part pk (repeatable); the rest stay outstanding")
a = ap.parse_args()

po = PurchaseOrder.objects.get(reference=a.reference)
if a.to.isdigit():
    dest = StockLocation.objects.get(pk=int(a.to))
else:
    hits = list(StockLocation.objects.filter(name=a.to)) or list(StockLocation.objects.filter(pathstring=a.to))
    if len(hits) != 1:
        print(f"{a.to!r} matches {len(hits)} locations - pass a pk or the full path:")
        for h in StockLocation.objects.filter(name=a.to):
            print(f"    {h.pk}  {h.pathstring}")
        sys.exit(1)
    dest = hits[0]

lines = {}
for ln in po.lines.select_related("part"):
    if a.part and ln.part.part_id not in a.part:
        lines[ln.pk] = {"packs": 0}
        print(f"  - skipped (not --part): {ln.part.part.name[:48]}")
    else:
        lines[ln.pk] = {"dest": dest.pk}
pl = engine.plan(po.pk, lines=lines, when=a.date or str(datetime.date.today()))

print(f"{po.reference}  status={po.status}  {po.description[:60]}\ndestination: {dest.pathstring}\n")
for x in pl["lines"]:
    print(f"  line qty {x['packs']:g} x pack {x['pack']:g} = {x['pieces']:g} pieces at ${x['unit']:.4f} each")
    print(f"     {x['name'][:56]}")
    print(f"     {x['before']:g} + {x['pieces']:g} = {x['before'] + x['pieces']:g} @ {dest.name}"
          f"{'  (merged)' if x['merge_into'] else '  (new row)'}")
if pl["warnings"]:
    print("\n!! PACK SIZE LOOKS WRONG — fix the SUPPLIER PART before receiving:")
    for w in pl["warnings"]:
        print(f"     {w}")
    sys.exit(1)
if not pl["lines"]:
    print("\nnothing outstanding to receive.")
if not a.commit:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

rc = engine.commit(pl)
for x in rc["lines"]:
    print(f"  + {x['pieces']:g} -> {x['dest_path']}  stock {x['stock']}  {x['url']}")
if rc["status"] == engine.COMPLETE:
    print(f"\n{po.reference} CLOSED — status 30")
else:
    print(f"\n{po.reference} left open — lines still outstanding")
print(f"undo receipt (valid until {rc['undo_until']}): {rc}")
