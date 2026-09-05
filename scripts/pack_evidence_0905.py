#!/usr/bin/env python3
"""Show the EVIDENCE behind every pack_audit flag, not just its verdict.

`pack_audit.py` prints "says 6 / pack_quantity 1" over a truncated title. That
is a verdict without its evidence, and it is not decidable: part 232 is
"XIAO ESP32C6 Pack", where the regex reads the 6 of "C6" followed by the word
"Pack" and announces a six-pack. Nothing in the audit's own output reveals
that — the title is cut off exactly where the proof would be.

So print, per flag: the full SKU, the full part name, the note, which pattern
fired, and the matched span with context. Then a human (or a run) can tell a
transcription from a guess, which is the standard the rest of this job holds
prices to.

Read-only. Writes nothing.
"""
import os
import re
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()

from company.models import SupplierPart  # noqa: E402
from order.models import PurchaseOrderLineItem  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402
from stock.models import StockItem  # noqa: E402

STRONG = [
    ('pcs/pieces', re.compile(r"(?<![\d.])(\d{1,5})\s*(?:pcs|pieces)\b", re.I)),
    ('pack of N', re.compile(r"\bpack\s*of\s*(\d{1,5})\b", re.I)),
    ('N-pack/pk', re.compile(r"(?<![\d.])(\d{1,5})\s*-?\s*(?:pack|pk)\b", re.I)),
    ('N pc', re.compile(r"(?<![\d.])(\d{1,5})\s*(?:pc)\b", re.I)),
]
DIMENSION = re.compile(
    r"\d\s*(?:mm|cm|m\b|in\b|inch|\"|'|ohm|k\b|v\b|w\b|a\b|hz|awg|uf|nf|pf|mh|x)\s*",
    re.I)
ASSORTMENT = re.compile(
    r"\b(?:assort\w*|kit\b|\bvalues?\b|variety|mixed|selection|set\b)", re.I)

OPEN = [PurchaseOrderStatus.PENDING.value, PurchaseOrderStatus.PLACED.value]

for sp in SupplierPart.objects.select_related('part', 'supplier').order_by('part__pk'):
    name = sp.part.name if sp.part else ''
    hay = f"{sp.SKU or ''} | {name} | {sp.note or ''}"
    pq = float(sp.pack_quantity_native or 1)
    found = []
    for label, pat in STRONG:
        for m in pat.finditer(hay):
            s = max(0, m.start() - 14)
            around = hay[s:m.end() + 14]
            if DIMENSION.search(around) and not re.search(
                    r"pcs|pieces|pack|\bpk\b", around, re.I):
                continue
            n = int(m.group(1))
            if 1 < n <= 10000:
                found.append((label, n, m.group(0), around))
    if not found:
        continue
    n = max(f[1] for f in found)
    if abs(pq - n) < 0.001 or ASSORTMENT.search(hay):
        continue

    pk = sp.part.pk if sp.part else '?'
    on_open = (PurchaseOrderLineItem.objects
               .filter(part=sp, order__status__in=OPEN).exists())
    stock = list(StockItem.objects.filter(part=sp.part)) if sp.part else []
    stock_s = ', '.join(f"{si.quantity.normalize():g}@{si.location or '-'}"
                        for si in stock) or 'none'

    print(f"\n=== part[{pk}]  native={pq:g}  regex says {n}  "
          f"{'ON OPEN PO' if on_open else 'no open PO'} ===")
    print(f"  supplier : {sp.supplier.name if sp.supplier else '?'}")
    print(f"  SKU      : {sp.SKU or '-'}")
    print(f"  name     : {name}")
    print(f"  note     : {sp.note or '-'}")
    print(f"  packtext : {sp.pack_quantity!r}")
    print(f"  stock    : {stock_s}")
    for label, num, matched, around in found:
        print(f"    match [{label}] -> {num}   on {matched!r}   in ...{around}...")
