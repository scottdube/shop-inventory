#!/usr/bin/env python3
"""Receive a purchase order whose goods were INSTALLED on arrival, and close it.

Written 2026-10-08 while Scott walked the open-PO list from the bench:
"po 171 rec all deployed at flight sim", "po 169 rec, deployed flight sim".
Hardware that is wired into the sim (or the building) is not inventory, but
the ORDER still has to be received and closed or it ages into OVERDUE.

What it does, per outstanding line:
  - books the pieces (pack-aware, piece price = line price / pack) as a stock
    row at --to, exactly as receive_po.py would, so the receipt is on record;
  - then takes the whole quantity straight back out with a DEPLOYED tracking
    entry, leaving the row at 0 with delete_on_deplete=False, so the part page
    still shows where it went and what it cost;
  - virtual parts (STL downloads) get no row at all, only the line receipt.
Then closes the order.

    itq run scripts/deploy_po.py PO-0169 --to 624 --why "flight sim cockpit"
    itq run scripts/deploy_po.py PO-0169 --to 624 --why "flight sim cockpit" --commit

Dry run by default. --keep <part_pk> [...] leaves those parts in stock
(the one plug of six that was not installed, etc).
"""
import argparse
import datetime
import os
import sys
from decimal import Decimal

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("reference")
ap.add_argument("--to", required=True, help="StockLocation pk the goods were received at")
ap.add_argument("--why", required=True, help="where it was installed, in Scott's words")
ap.add_argument("--keep", nargs="*", type=int, default=[], help="part pks NOT deployed")
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

po = PurchaseOrder.objects.get(reference=a.reference)
dest = StockLocation.objects.get(pk=int(a.to))
user = User.objects.filter(is_superuser=True).first()
when = datetime.date.today()
print(f"{po.reference}  status={po.status}  {po.description[:60]}")
print(f"received at {dest.pathstring}, deployed: {a.why}\n")

plan = []
for ln in po.lines.all():
    outstanding = float(ln.quantity) - float(ln.received)
    if outstanding <= 0:
        print(f"  = already received: {ln.part.part.name[:50]}")
        continue
    sp = ln.part
    pack = float(sp.pack_quantity_native or 1)
    pieces = outstanding * pack
    unit = Decimal(str(ln.purchase_price.amount)) / Decimal(str(pack))
    keep = sp.part.pk in a.keep
    virt = sp.part.virtual
    plan.append((ln, sp, pack, pieces, unit, keep, virt))
    tag = "VIRTUAL, no row" if virt else ("KEEP in stock" if keep else "DEPLOY -> 0")
    print(f"  {outstanding:g} x pack {pack:g} = {pieces:g} at ${unit:.4f}  {tag}")
    print(f"     {sp.part.name[:60]}")

if not a.commit:
    print("\nDRY RUN - nothing written. Re-run with --commit.")
    sys.exit(0)

for ln, sp, pack, pieces, unit, keep, virt in plan:
    if not virt:
        row = StockItem.objects.create(
            part=sp.part, location=dest, quantity=pieces,
            supplier_part=sp, purchase_order=po,
            purchase_price=unit, purchase_price_currency="USD",
            delete_on_deplete=False,
            notes=(f"RECEIVED {pieces:g} on {when} from {po.reference} at ${unit:.4f} each "
                   f"(line qty {float(ln.quantity):g} x pack {pack:g})."))
        row.refresh_from_db()
        assert float(row.quantity) == pieces, "quantity did not stick"
        if not keep:
            row.take_stock(pieces, user, notes=(
                f"DEPLOYED: {a.why} (Scott, {when}). Installed hardware leaves "
                f"inventory; row kept at 0 as the receipt record."))
            row.refresh_from_db()
            assert float(row.quantity) == 0, "deploy did not stick"
        print(f"  + row {row.pk}: {sp.part.name[:44]} -> {float(row.quantity):g}")
    ln.received = ln.quantity
    ln.save(); ln.refresh_from_db()
    assert float(ln.received) == float(ln.quantity), "line did not mark received"

po.refresh_from_db()
if all(float(l.received) >= float(l.quantity) for l in po.lines.all()):
    PurchaseOrder.objects.filter(pk=po.pk).update(status=30, complete_date=when)
    po.refresh_from_db()
    assert po.status == 30, "order did not close"
    print(f"\n{po.reference} CLOSED - status 30, complete_date {po.complete_date}")
else:
    print(f"\n{po.reference} left open - lines still outstanding")
