"""Set the price on the ELEGOO perfboard kit (stock 1225) from Amazon order history, 2026-11-02.

Scott: "Chk amazon last season". Order History.csv (Amazon data export in
~/Downloads/Your Orders) has exactly one line for ASIN B072Z7Y19F: order
113-5814816-7797840, 2026-03-15, shipped to the LRD address, qty 1, unit price
$8.99 (+ $0.63 tax). One purchase, to LRD, last season - so this kit is that
order. Unit price before tax, as on the other rows.

    itq run scripts/elegoo_perfboard_price_1102.py [--commit]
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from djmoney.money import Money  # noqa: E402
from common.models import Note  # noqa: E402
from stock.models import StockItem  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

ADD = ("<p>Price from Amazon order 113-5814816-7797840, 2026-03-15, shipped to LRD, 1 kit at $8.99 "
       "(+$0.63 tax); the only purchase of ASIN B072Z7Y19F in the Amazon order export (set 2026-11-02).</p>")
s = StockItem.objects.get(pk=1225)
assert s.part.name.startswith("ELEGOO Double Sided PCB"), s.part.name
assert s.purchase_price is None, s.purchase_price
n = s.notes.get(title="Source")
print(f"stock 1225 price None -> $8.99; note += {ADD}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

StockItem.objects.filter(pk=1225).update(purchase_price=Money(8.99, "USD"))
Note.objects.filter(pk=n.pk).update(content=n.content + "\n" + ADD)

# Verify by re-read.
s = StockItem.objects.get(pk=1225)
n = Note.objects.get(pk=n.pk)
print(f"stock 1225 price {s.purchase_price}; note ends: ...{n.content[-120:]}")
print("ALL VERIFIED" if s.purchase_price == Money(8.99, "USD") and "113-5814816-7797840" in n.content else "NOT VERIFIED")
