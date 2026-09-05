#!/usr/bin/env python3
"""Pack exposure on OPEN purchase orders — the lines a human is about to receive.

`pack_audit.py --all` says 31 supplier parts state a piece count while their
`pack_quantity_native` is 1. That is the whole install, most of it historic. The
number that decides whether tonight matters is a smaller one: **how many of
those sit on a PO that has not been received yet**, because CLAUDE.md's rule is
"run the check BEFORE receiving" and a pack error only becomes stock damage at
the moment the box is booked in.

Read-only. Status codes come from the enum, and the histogram is printed beside
the answer, per the 2026-09-03 `status=10 is not Placed` trap.
"""
import os
import re
import sys
from decimal import Decimal, InvalidOperation

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()

from order.models import PurchaseOrder  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402

# Same STRONG patterns and DIMENSION guard as pack_audit.py. Deliberately a
# copy and not an import: itq ships exactly one file to the Mini, so a sibling
# import would not resolve there. If pack_audit's patterns change, change these.
STRONG = [
    re.compile(r"(?<![\d.])(\d{1,5})\s*(?:pcs|pieces)\b", re.I),
    re.compile(r"\bpack\s*of\s*(\d{1,5})\b", re.I),
    re.compile(r"(?<![\d.])(\d{1,5})\s*-?\s*(?:pack|pk)\b", re.I),
    re.compile(r"(?<![\d.])(\d{1,5})\s*(?:pc)\b", re.I),
]
DIMENSION = re.compile(
    r"\d\s*(?:mm|cm|m\b|in\b|inch|\"|'|ohm|k\b|v\b|w\b|a\b|hz|awg|uf|nf|pf|mh|x)\s*",
    re.I)
ASSORTMENT = re.compile(
    r"\b(?:assort\w*|kit\b|\bvalues?\b|variety|mixed|selection|set\b)", re.I)


def hits(text):
    out = []
    for p in STRONG:
        for m in p.finditer(text or ''):
            s = max(0, m.start() - 12)
            around = (text or '')[s:m.end() + 12]
            if DIMENSION.search(around) and not re.search(
                    r"pcs|pieces|pack|\bpk\b", around, re.I):
                continue
            n = int(m.group(1))
            if 1 < n <= 10000:
                out.append(n)
    return out


print("--- PO status histogram (enum-named, never a literal) ---")
for st in PurchaseOrderStatus.values():
    n = PurchaseOrder.objects.filter(status=st).count()
    if n:
        print(f"  {int(st):>3} {PurchaseOrderStatus.label(st):<12} : {n}")

OPEN = [PurchaseOrderStatus.PENDING.value, PurchaseOrderStatus.PLACED.value]
flagged = clean = 0

for po in PurchaseOrder.objects.filter(status__in=OPEN).order_by('reference'):
    lines = list(po.lines.all())
    print(f"\n=== {po.reference}  {PurchaseOrderStatus.label(po.status)}  "
          f"ref={po.supplier_reference!r}  "
          f"{po.supplier.name if po.supplier else '?'}  "
          f"({len(lines)} line{'s' if len(lines) != 1 else ''}) ===")
    for ln in lines:
        sp = ln.part
        if not sp:
            print("   (line with no supplier part)")
            continue
        name = sp.part.name if sp.part else '?'
        hay = f"{sp.SKU or ''} | {name} | {sp.note or ''}"
        pq = float(sp.pack_quantity_native or 1)
        try:
            txt = Decimal(str(sp.pack_quantity).strip() or '1')
        except (InvalidOperation, ValueError, TypeError):
            txt = None
        split = (txt is not None and txt != sp.pack_quantity_native)
        s = hits(hay)
        n = max(s) if s else None
        bad = (n is not None and abs(pq - n) >= 0.001
               and not ASSORTMENT.search(hay))
        mark = '!!' if (bad or split) else '  '
        if bad or split:
            flagged += 1
        else:
            clean += 1
        print(f" {mark} qty={ln.quantity!s:>6}  packtext={str(sp.pack_quantity)[:6]:>6} "
              f"native={pq:g}  says={n if n else '-'}   part[{sp.part.pk if sp.part else '?'}]")
        print(f"        SKU  : {(sp.SKU or '')[:66]}")
        print(f"        name : {name[:66]}")

print(f"\nopen-PO lines flagged: {flagged}   clean: {clean}")
