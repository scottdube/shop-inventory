"""Show StockItem rows by PK, and every stock row for a part by PK.

Read-only. Written 2026-08-25 to settle a contradiction the daytime sweep found:
`docs/OPEN.md` says "the QL-810W is stocked 1 @ SLN/Electronics Bench (stock
#570)" while `received_no_stock.py` reports part #1057 (QL-810W) holding ZERO
StockItem rows. Both cannot be true, and which one is wrong decides whether
tomorrow's replacement gets checked in against an existing row or a new one.

Usage:  itq run scripts/stock_show.py --stock 570
        itq run scripts/stock_show.py --part 1057
"""

import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockItem  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--stock", type=int, action="append", default=[])
ap.add_argument("--part", type=int, action="append", default=[])
a = ap.parse_args()


def show(it):
    print(f"stock #{it.pk}  qty={it.quantity}  status={it.get_status_display()}")
    print(f"  part #{it.part.pk} {it.part.full_name}")
    print(f"  location: {it.location.pathstring if it.location else '(none)'}")
    print(f"  serial={it.serial}  batch={it.batch}  deleted_on={getattr(it, 'delete_on', None)}")
    if it.purchase_order:
        print(f"  purchase_order: {it.purchase_order.reference}")
    if it.notes:
        print(f"  notes: {it.notes.strip()[:300]}")
    print()


for pk in a.stock:
    it = StockItem.objects.filter(pk=pk).first()
    if it is None:
        print(f"stock #{pk}: NO SUCH ROW\n")
    else:
        show(it)

for pk in a.part:
    rows = StockItem.objects.filter(part__pk=pk)
    print(f"part #{pk}: {rows.count()} stock row(s)")
    for it in rows:
        show(it)
    print()
