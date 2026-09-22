"""Backfill SupplierPriceBreak from the PO line that already records the cost.

Found 2026-09-22 while re-deriving queue B: 123 of 746 supplier parts carry no
price break at all, and 11 suppliers sit at ZERO — Mouser, DigiKey, Seeed, eBay,
LCSC, Walmart, JLCPCB, MSC and more. A part with no price break shows no supplier
price anywhere InvenTree does pricing, even when the cost is sitting on its own
purchase order one join away.

**This invents nothing.** The source is `PurchaseOrderLineItem.purchase_price` —
the vendor's own order line, which the guardrail names as the one allowed source
of cost — and it is already denominated per SUPPLIER UNIT, the same denomination
a price break uses. So it copies 1:1 with no arithmetic.

THE PACK QUESTION, settled by measurement rather than assumed: the line price is
per PACK, not per piece. Four rows carry both a line price and a per-piece stock
cost and all four divide exactly by `pack_quantity_native` — sp=693 $57.46/59 =
$0.974, sp=688 $9.49/5 = $1.898, sp=704 $14.99/3 = $5.00, sp=705 $17.99/2 =
$9.00. That is the convention `receive_line_item()` implements, so a pack row
needs no conversion either. **But the same check is a guard**: where a stock cost
exists and does NOT reconcile to line/native within a cent, one of the two
numbers is wrong, and this script SKIPS that row rather than propagate a number
it cannot corroborate.

Deliberately NOT done here:
  - the 10 rows whose only cost is `StockItem.purchase_price` (MSC 29/30, Mouser
    7/8, Seeed 1-6). A stock cost is not an order line, so it is a weaker source
    than the guardrail names. Queued for Scott instead.
  - the 38 rows with no cost anywhere, 10 of which are the Tormach DIRECTPAY
    parts already on the decision queue as `tormach-directpay-prices`.

Never overwrites: a supplier part that already has any break is skipped by
construction. Every write is verified by re-reading the row.

Usage:  breaks_backfill_0922.py [--commit]
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart, SupplierPriceBreak  # noqa: E402
from order.models import PurchaseOrderLineItem  # noqa: E402
from stock.models import StockItem  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

have = set(SupplierPriceBreak.objects.values_list("part_id", flat=True))
gap = SupplierPart.objects.exclude(pk__in=have).order_by("supplier__name", "pk")

wrote = skipped_nocost = skipped_mismatch = skipped_zero = skipped_pack = failed = 0
for sp in gap:
    line = (PurchaseOrderLineItem.objects.filter(part=sp)
            .exclude(purchase_price=None).order_by("-pk").first())
    if line is None:
        skipped_nocost += 1
        continue

    # A $0.00 break is WORSE than no break: it does not read as "unknown", it
    # reads as FREE, and it propagates into every BOM rollup that part appears
    # in. LCSC rounds sub-cent parts to 0.00 on the order line (C2907219 10k
    # 0805, C95781 1k 0805), so this is a real row, not a hypothetical.
    if float(line.purchase_price.amount) <= 0:
        print(f"0  sp={sp.pk} {sp.SKU!r}: order line reads {line.purchase_price} — SKIPPED, "
              f"a zero break reads as FREE, not as unknown")
        skipped_zero += 1
        continue

    native = float(sp.pack_quantity_native or 1)
    stock = (StockItem.objects.filter(supplier_part=sp)
             .exclude(purchase_price=None).order_by("-pk").first())
    if stock is not None and native:
        expect = float(line.purchase_price.amount) / native
        got = float(stock.purchase_price.amount)
        if abs(expect - got) > 0.01:
            print(f"!! sp={sp.pk} {sp.SKU!r}: line {line.purchase_price} / native {native:g} "
                  f"= {expect:.4f} but stock reads {stock.purchase_price} — SKIPPED, "
                  f"one of the two is wrong and neither is corroborated")
            skipped_mismatch += 1
            continue

    # Pack row with no stock cost to reconcile against: the per-pack convention
    # is CORROBORATED on four rows but cannot be CHECKED here, and one of these
    # is visibly wrong on its face — sp=586, $0.15 for twenty KF301 terminal
    # blocks, which is a per-piece price sitting on a pack line. Held back for
    # Scott rather than guessed at either denomination.
    if native != 1 and stock is None:
        print(f"?  sp={sp.pk} {sp.SKU[:18]!r} native={native:g} line={line.purchase_price} "
              f"— HELD, pack denomination uncorroborated (per pack = "
              f"{float(line.purchase_price.amount) / native:.4f}/piece)")
        skipped_pack += 1
        continue

    if not a.commit:
        print(f"~  sp={sp.pk:4d} {sp.SKU[:18]:18s} {sp.supplier.name[:16]:16s} "
              f"native={native:<4g} <- {line.purchase_price} ({line.order.reference}) "
              f"#{sp.part.pk} {sp.part.name[:32]}")
        continue

    SupplierPriceBreak.objects.create(part=sp, quantity=1, price=line.purchase_price)
    fresh = list(SupplierPriceBreak.objects.filter(part=sp))
    if len(fresh) == 1 and fresh[0].price == line.purchase_price:
        print(f"+  sp={sp.pk:4d} {sp.SKU[:18]:18s} {fresh[0].price} "
              f"#{sp.part.pk} {sp.part.name[:36]}")
        wrote += 1
    else:
        print(f"!! sp={sp.pk}: write did not stick "
              f"({[(str(b.quantity), str(b.price)) for b in fresh]})")
        failed += 1

total = SupplierPart.objects.count()
now_have = set(SupplierPriceBreak.objects.values_list("part_id", flat=True))
print(f"\nwrote={wrote} skipped_no_order_line={skipped_nocost} "
      f"skipped_zero_price={skipped_zero} skipped_mismatch={skipped_mismatch} "
      f"held_pack_uncorroborated={skipped_pack} failed_verify={failed}"
      f"{'  (DRY RUN)' if not a.commit else ''}")
print(f"price-break coverage: {len(now_have)} / {total} "
      f"({100.0 * len(now_have) / total:.1f}%)")
