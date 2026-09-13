"""Read-only: for the 87 MULTIPACK candidates, is the part stocked as PIECES or
as ONE BAG?

This is the question that decides whether the 87 flags are defects at all, and
it is answerable from data already in the system rather than from the vendor's
prose. Two shapes exist and they need opposite treatment:

  PIECES   the drawer walk counted individual units (37 zip ties, 8 diodes), so
           the part's unit IS the piece. pack_quantity 1 is then WRONG: one
           purchased line delivered N pieces, and the receipt books 1 at the
           whole-bag price — a factor-of-N cost error per piece.

  ONE BAG  stock reads 1 and the location holds a single unopened bag, so the
           part IS the bag. pack_quantity 1 is CORRECT and changing it would
           corrupt a correct record.

So the count in stock, not the title, is the discriminator. Where a part has no
stock at all the question is still open and is reported as its own bucket —
those cannot be settled by measurement yet, only by a drawer.

Nothing is written. The point is to turn 87 undecidable lines into a small
number of buckets Scott can rule on in one pass.
"""
import os
import re
import sys
from decimal import Decimal, InvalidOperation

import django
from django.db.models import Sum

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart          # noqa: E402
from order.models import PurchaseOrderLineItem    # noqa: E402
from stock.models import StockItem                # noqa: E402

PACK_RE = [
    re.compile(r"(?<![\d.])(\d{1,4})\s*[- ]?\s*(?:pack|packs|pcs|pieces|piece|count|ct)\b", re.I),
    re.compile(r"pack\s+of\s+(\d{1,4})\b", re.I),
    re.compile(r"(?<![\d.])(\d{1,4})\s*[- ]?\s*p[cs]s?\b", re.I),
]
KIT_RE = re.compile(
    r"\b(sets?|kits?|assortment|assorted|variety|boxed|in fitted box|"
    r"combo|bundle|selection)\b",
    re.I,
)


def pack_from_title(text):
    found = []
    for rx in PACK_RE:
        for m in rx.finditer(text or ""):
            try:
                n = int(m.group(1))
            except ValueError:
                continue
            if 1 < n <= 5000:
                found.append(n)
    return max(found) if found else None


def as_dec(v):
    if v in (None, ""):
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


pieces, onebag, nostock = [], [], []

for sp in SupplierPart.objects.select_related("part", "supplier").order_by("pk"):
    native = as_dec(sp.pack_quantity_native)
    if native is not None and native != 1:
        continue
    title = " | ".join(
        str(x) for x in (sp.part.name, sp.part.description, sp.note, sp.SKU) if x
    )
    n = pack_from_title(title)
    if not n or KIT_RE.search(title):
        continue

    qty = StockItem.objects.filter(part=sp.part).aggregate(q=Sum("quantity"))["q"]
    priced = (
        PurchaseOrderLineItem.objects.filter(part=sp)
        .exclude(purchase_price=None)
        .exists()
    )
    row = (sp, n, qty, priced)
    if qty is None or qty == 0:
        nostock.append(row)
    elif qty == 1:
        onebag.append(row)
    else:
        pieces.append(row)


def show(label, rows, note):
    print(f"\n-- {label}: {len(rows)} --   {note}")
    for sp, n, qty, priced in rows:
        p = "priced" if priced else "no-price"
        print(f"   SP {sp.pk:4d} | pack says {n:4d} | stock {qty} | {p} | #{sp.part.pk} {sp.part.name[:52]}")


total = len(pieces) + len(onebag) + len(nostock)
print(f"MULTIPACK candidates re-examined : {total}")
print(f"  stocked in PIECES (>1)  : {len(pieces)}   <- pack 1 is probably WRONG")
print(f"  stocked as ONE unit (1)  : {len(onebag)}   <- pack 1 may be CORRECT (part = the bag)")
print(f"  no stock at all          : {len(nostock)}  <- undecidable without a drawer")

show("PIECES", pieces, "a count in pieces means the unit is the piece")
show("ONE UNIT", onebag, "stock of exactly 1 reads as one unopened bag")
show("NO STOCK", nostock, "nothing counted yet; leave alone")
