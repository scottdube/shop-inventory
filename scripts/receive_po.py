#!/usr/bin/env python3
"""Receive a purchase order: pack-aware, merging, and it CLOSES THE ORDER.

Written 2026-09-01 after receiving two POs by hand and getting a different half
wrong each time.

InvenTree's own receive_line_item() is not used here for one reason: it ignores
pack_quantity and books the whole pack price against a single piece. That is the
$208.62-for-19-bins failure, and it nearly repeated with a 5-pack of Hi-Links
booked as one piece at $16.96.

But hand-rolling the receive lost the OTHER half. Setting line.received satisfies
the line and leaves the ORDER at PLACED, so a fully-received order ages into
OVERDUE and shows up on the purchasing screen as outstanding. Scott found two
sitting like that.

Receiving a line is not closing an order. This does both.

    itq run scripts/receive_po.py PO-0146 --to RB-14
    itq run scripts/receive_po.py PO-0146 --to RB-14 --commit

Default is a DRY RUN that prints what it would book. Nothing is written without
--commit, because a receive that is wrong about pack size is silently wrong -
the quantity looks plausible and the price per piece is off by the pack factor.
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

from order.models import PurchaseOrder  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("reference")
ap.add_argument("--to", required=True, help="destination StockLocation name")
ap.add_argument("--commit", action="store_true")
ap.add_argument("--date", default=None, help="receive date, default today")
a = ap.parse_args()

po = PurchaseOrder.objects.get(reference=a.reference)
# "Receiving" is the name of TWO locations (SLN and LRD), and .get(name=...)
# raised MultipleObjectsReturned on it. Accept a pk or a full pathstring too,
# and on ambiguity print the candidates instead of failing opaquely.
if a.to.isdigit():
    dest = StockLocation.objects.get(pk=int(a.to))
else:
    hits = list(StockLocation.objects.filter(name=a.to))
    if len(hits) != 1:
        hits = list(StockLocation.objects.filter(pathstring=a.to))
    if len(hits) != 1:
        cands = StockLocation.objects.filter(name=a.to)
        print(f"{a.to!r} matches {cands.count()} locations - be specific "
              f"(pass a pk or the full path):")
        for h in cands:
            print(f"    {h.pk}  {h.pathstring}")
        sys.exit(1)
    dest = hits[0]
when = (datetime.date.fromisoformat(a.date) if a.date else datetime.date.today())

print(f"{po.reference}  status={po.status}  {po.description[:60]}")
print(f"destination: {dest.pathstring}\n")

plan, warn = [], []
for ln in po.lines.all():
    outstanding = float(ln.quantity) - float(ln.received)
    if outstanding <= 0:
        print(f"  = line already received in full: {ln.part.part.name[:48]}")
        continue
    sp = ln.part
    pack = float(sp.pack_quantity_native or 1)
    pieces = outstanding * pack
    unit = Decimal(str(ln.purchase_price.amount)) / Decimal(str(pack))

    # The pack size is the thing most likely to be wrong. Say it out loud.
    sku = (sp.SKU or "").lower()
    name = (sp.part.name or "").lower()
    if pack == 1 and any(w in f"{sku} {name}" for w in ("pcs", "pack", " pk", "pieces")):
        warn.append(f"{sp.part.name[:44]} — SKU says a pack, pack_quantity is 1")

    row = StockItem.objects.filter(part=sp.part, location=dest).first()
    before = float(row.quantity) if row else 0.0
    plan.append((ln, sp, pack, pieces, unit, row, before))
    print(f"  line qty {outstanding:g} x pack {pack:g} = {pieces:g} pieces "
          f"at ${unit:.4f} each")
    print(f"     {sp.part.name[:56]}")
    print(f"     {before:g} + {pieces:g} = {before + pieces:g} @ {dest.name}"
          f"{'  (new row)' if not row else '  (merged)'}")

if warn:
    print("\n!! PACK SIZE LOOKS WRONG — fix the SUPPLIER PART before receiving:")
    for w in warn:
        print(f"     {w}")
    print("   Receiving now books the whole pack price against one piece.")
    sys.exit(1)

if not plan:
    print("\nnothing outstanding to receive.")

if not a.commit:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

for ln, sp, pack, pieces, unit, row, before in plan:
    if row:
        row.quantity = before + pieces
        row.notes = (row.notes or "") + (
            f"\n\nRECEIVED {pieces:g} on {when} from {po.reference} at ${unit:.4f} each. "
            f"Merged into this row: once goods are in inventory the shelf answers "
            f"'how many' in ONE number. {before:g} + {pieces:g} = {before + pieces:g}.")
        row.save()
    else:
        row = StockItem.objects.create(
            part=sp.part, location=dest, quantity=pieces,
            purchase_price=unit, purchase_price_currency="USD",
            notes=(f"RECEIVED {pieces:g} on {when} from {po.reference} at "
                   f"${unit:.4f} each (line qty {float(ln.quantity):g} x pack {pack:g})."))
    row.refresh_from_db()
    assert float(row.quantity) == before + pieces, "quantity did not stick"
    ln.received = ln.quantity
    ln.save(); ln.refresh_from_db()
    assert float(ln.received) == float(ln.quantity), "line did not mark received"
    print(f"  + {pieces:g} -> {dest.name}, {po.reference} line satisfied")

# THE HALF THAT WAS MISSED TWICE.
po.refresh_from_db()
if all(float(l.received) >= float(l.quantity) for l in po.lines.all()):
    po.status = 30
    po.complete_date = when
    po.save(); po.refresh_from_db()
    if po.status != 30:
        PurchaseOrder.objects.filter(pk=po.pk).update(status=30, complete_date=when)
        po.refresh_from_db()
    assert po.status == 30, "order did not close"
    print(f"\n{po.reference} CLOSED — status 30, complete_date {po.complete_date}")
else:
    print(f"\n{po.reference} left open — lines still outstanding")
