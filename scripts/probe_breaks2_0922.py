"""The 123 supplier parts with no price break — is the price recoverable, and from where?

Probe 1 of this pair found breaks are the house norm (623 of 746, 83.5%) but 11
suppliers sit at zero, so this is a 123-row gap and not the 2-row MSC anomaly it
looked like. This one asks whether a backfill could be done WITHOUT inventing
anything, and names the trap that would make it wrong.

Three possible sources per row, in decreasing trustworthiness:

  PO line   PurchaseOrderLineItem.purchase_price — the vendor's own order line,
            denominated per SUPPLIER UNIT (i.e. per pack). This is what a
            SupplierPriceBreak is also denominated in, so it copies across 1:1.
  stock     StockItem.purchase_price — per PIECE. For a pack of 10 this is the
            line price / 10, so copying it into a price break would understate
            the pack price by the pack factor. THE TRAP.
  nothing   no cost recorded anywhere; blocked by never-invent-prices.

Prints the counts, and flags every row where pack_quantity_native != 1, because
those are exactly the rows where the two sources disagree by construction.

Read-only.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart, SupplierPriceBreak  # noqa: E402
from order.models import PurchaseOrderLineItem  # noqa: E402
from stock.models import StockItem  # noqa: E402

with_break = set(SupplierPriceBreak.objects.values_list("part_id", flat=True))
gap = SupplierPart.objects.exclude(pk__in=with_break).order_by("supplier__name", "pk")

from_po = from_stock = nothing = packs = both_disagree = 0
rows = []
for sp in gap:
    lines = list(PurchaseOrderLineItem.objects.filter(part=sp)
                 .exclude(purchase_price=None).order_by("-pk"))
    stocks = list(StockItem.objects.filter(supplier_part=sp)
                  .exclude(purchase_price=None).order_by("-pk"))
    native = float(sp.pack_quantity_native or 1)
    src = "nothing"
    if lines:
        src = "PO line"
        from_po += 1
    elif stocks:
        src = "stock"
        from_stock += 1
    else:
        nothing += 1
    if native != 1:
        packs += 1
    if lines and stocks:
        lp = float(lines[0].purchase_price.amount)
        st = float(stocks[0].purchase_price.amount)
        if abs(lp - st) > 0.005:
            both_disagree += 1
    rows.append((sp, src, native, lines[:1], stocks[:1]))

print(f"no price break: {gap.count()}")
print(f"  recoverable from a PO line : {from_po}")
print(f"  only a stock cost (per PIECE, pack trap applies): {from_stock}")
print(f"  no cost anywhere (blocked)  : {nothing}")
print(f"  of all of the above, pack_quantity_native != 1 : {packs}")
print(f"  rows where PO line and stock cost DISAGREE     : {both_disagree}")

print("\n--- every row that is NOT 'nothing', by supplier ---")
last = None
for sp, src, native, lines, stocks in rows:
    if src == "nothing":
        continue
    if sp.supplier.name != last:
        last = sp.supplier.name
        print(f"\n{last}")
    lp = str(lines[0].purchase_price) if lines else "-"
    st = str(stocks[0].purchase_price) if stocks else "-"
    po = lines[0].order.reference if lines else "-"
    warn = "  PACK" if native != 1 else ""
    print(f"  sp={sp.pk:4d} {sp.SKU[:16]:16s} native={native:g} src={src:7s} "
          f"po={po:8s} line={lp:>12s} stock={st:>12s}{warn}  #{sp.part.pk} "
          f"{sp.part.name[:34]}")

print("\n--- suppliers at zero coverage, and how much of each is blocked ---")
byname = {}
for sp, src, native, _l, _s in rows:
    d = byname.setdefault(sp.supplier.name, {"PO line": 0, "stock": 0, "nothing": 0})
    d[src] += 1
for name in sorted(byname):
    d = byname[name]
    print(f"  {name[:34]:34s} po={d['PO line']:3d} stock={d['stock']:3d} "
          f"none={d['nothing']:3d}")
