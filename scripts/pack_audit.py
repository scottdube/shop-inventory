#!/usr/bin/env python3
"""Supplier parts whose SKU says "multipack" while pack_quantity says 1.

Scott, 2026-09-01: "We seem to have this problem every time we buy something
that comes in a multipack. There's something wrong with the way the rules are
written or the way it's being interpreted, because it happens every time."

He is right, and it is neither the rule nor the interpretation. CLAUDE.md says
"a pack is a supplier fact, not a part; stock is counted in PIECES and the
supplier part carries pack_quantity". Measured 2026-09-01: **688 of 706 supplier
parts carry pack_quantity = 1**. The rule is not misapplied. It is UNAPPLIED,
because nothing ever asks the question at the moment a supplier part is born.

Supplier parts are created by importers from order history. An order line says
"1 x <seller's title>" whether that is one screw or one bag of fifty, so the
importer takes InvenTree's default of 1 and the pack size stays buried in the
title. Nobody notices until goods land and the price per piece is absurd -
19 storage bins at $208.62, a pack of 5 Hi-Links booked as one piece at $16.96.

A principle in a document cannot fix this. A check before receiving can.

    itq run scripts/pack_audit.py                 # high-confidence only
    itq run scripts/pack_audit.py --all           # include weak signals
    itq run scripts/pack_audit.py --po PO-0146    # just one order's lines

Exit code 1 when anything high-confidence is unresolved, so it can gate a
receive.
"""
import argparse
import os
import re
import sys
from decimal import Decimal, InvalidOperation

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402

# HIGH confidence: these phrasings mean count-of-pieces and nothing else.
#
# The look-behind excludes a preceding LETTER as well as a digit or dot, and
# that is not cosmetic — without it the audit read pack counts out of the middle
# of identifiers (2026-09-05):
#
#   B01983R7PK          -> "7PK"   claimed a 7-pack of an Arducam Nano
#   XIAO ESP32C6 Pack   -> "6 Pack" claimed a 6-pack of a single XIAO board
#
# Both are letter-then-digit tokens: an Amazon ASIN and a chip name. `(?<![\d.])`
# happily matched inside them, and the audit's own output truncated the title
# just short of the evidence, so the verdict looked as solid as the 29 real ones
# beside it. A pack count must start at a token boundary.
STRONG = [
    re.compile(r"(?<![\d.A-Za-z])(\d{1,5})\s*(?:pcs|pieces)\b", re.I),
    re.compile(r"\bpack\s*of\s*(\d{1,5})\b", re.I),
    re.compile(r"(?<![\d.A-Za-z])(\d{1,5})\s*-?\s*(?:pack|pk)\b", re.I),
    re.compile(r"(?<![\d.A-Za-z])(\d{1,5})\s*(?:pc)\b", re.I),
]
# WEAK: "set", "kit", "lot" — often a count, often an assortment sold as one unit.
WEAK = [re.compile(r"(?<![\d.A-Za-z])(\d{1,5})\s*(?:set|lot|bag)\b", re.I)]

# A number touching a unit is a DIMENSION, never a pack count. This is the
# lesson from the first draft, which flagged a 2000x microscope and a
# 150 x 100 x 0.8mm PCB as 2000-packs and 150-packs.
DIMENSION = re.compile(
    r"\d\s*(?:mm|cm|m\b|in\b|inch|\"|'|ohm|k\b|v\b|w\b|a\b|hz|awg|uf|nf|pf|mh|x)\s*",
    re.I)


def hits(text, pats):
    out = []
    for p in pats:
        for m in p.finditer(text or ""):
            s = max(0, m.start() - 12)
            around = (text or "")[s:m.end() + 12]
            if DIMENSION.search(around) and not re.search(
                    r"pcs|pieces|pack|\bpk\b", around, re.I):
                continue
            n = int(m.group(1))
            if 1 < n <= 10000:
                out.append(n)
    return out


ap = argparse.ArgumentParser()
ap.add_argument("--all", action="store_true", help="include weak signals too")
ap.add_argument("--po", help="restrict to the lines of one purchase order")
a = ap.parse_args()

if a.po:
    po = PurchaseOrder.objects.get(reference=a.po)
    sps = [ln.part for ln in po.lines.all() if ln.part]
    scope = f"lines of {a.po}"
else:
    sps = SupplierPart.objects.all().select_related("part")
    scope = "every supplier part"

# An ASSORTMENT is not a multipack, and this is the distinction that makes the
# tool trustworthy. "24 Values 480pcs Capacitor Kit" holds 480 pieces that are
# NOT interchangeable; pack_quantity=480 would claim 480 of one thing. Such a kit
# is one unit (and if its contents ever need finding, it becomes a LOCATION -
# see docs/TECHNIQUES.md, the four screw kits). A "50 PCS 392 fuse" of one value
# is a genuine multipack and pack_quantity really is 50.
ASSORTMENT = re.compile(
    r"\b(?:assort\w*|kit\b|\bvalues?\b|variety|mixed|selection|set\b)", re.I)

# THE EXACT CHECK, which needs no regex and has no false positives.
# SupplierPart stores the pack TWICE: `pack_quantity` is text a human types and
# every screen shows, `pack_quantity_native` is the Decimal receiving actually
# multiplies by. Only clean() derives the second from the first, and save()
# calls clean() -- but a queryset .update(pack_quantity='5') does not. The text
# then reads 5, native stays 1, and receiving silently drops the pack.
#
# Five supplier parts were in that state on 2026-09-03, and this audit could not
# see any of them: it compared the SKU STRING against native, and a name like
# "Copper Clad Laminate PCB 150 x 100 x 0.8mm" states no piece count to compare.
# Comparing the two pack fields to EACH OTHER catches it exactly.
divergent = []
for sp in sps:
    try:
        txt = Decimal(str(sp.pack_quantity).strip() or "1")
    except (InvalidOperation, ValueError, TypeError):
        divergent.append((sp, None))
        continue
    if txt != sp.pack_quantity_native:
        divergent.append((sp, txt))

strong_bad, weak_bad, agree, kits = [], [], [], []
for sp in sps:
    hay = f"{sp.SKU or ''} | {sp.part.name if sp.part else ''} | {sp.note or ''}"
    pq = float(sp.pack_quantity_native or 1)
    s = hits(hay, STRONG)
    w = hits(hay, WEAK)
    if s:
        n = max(s)
        if abs(pq - n) < 0.001:
            agree.append((sp, n, pq))
        elif ASSORTMENT.search(hay):
            kits.append((sp, n, pq))
        else:
            strong_bad.append((sp, n, pq))
    elif w and a.all:
        weak_bad.append((sp, max(w), pq))

print(f"PACK AUDIT — {scope}")
print(f"  pack text disagrees with pack native     : {len(divergent)}  <-- worst kind")
print(f"  SKU says a pack AND pack_quantity agrees : {len(agree)}")
print(f"  SKU says a pack AND pack_quantity is 1   : {len(strong_bad)}  <-- fix these")

if divergent:
    print("\nSPLIT-BRAIN PACK — the record already knows the pack size and "
          "receiving will still ignore it:")
    for sp, txt in divergent:
        shown = "UNPARSEABLE" if txt is None else f"{txt.normalize():g}"
        print(f"   text {str(sp.pack_quantity)[:10]:>10} / native "
              f"{sp.pack_quantity_native.normalize():g}   -> should be {shown}")
        print(f"        {(sp.part.name if sp.part else '')[:72]}")
    print("  Repair with scripts/fix_pack_native.py, which writes through save() "
          "so clean() runs.")

if strong_bad:
    print("\nHIGH CONFIDENCE — the SKU states a piece count:")
    for sp, n, pq in sorted(strong_bad, key=lambda r: -r[1]):
        print(f"   says {n:>5} / pack_quantity {pq:g}   part [{sp.part.pk if sp.part else '?'}]")
        print(f"        {(sp.SKU or '')[:64]}")
        print(f"        {(sp.part.name if sp.part else '')[:72]}")

if kits:
    print(f"\nASSORTMENTS — correctly pack_quantity 1, NOT a bug ({len(kits)}):")
    print("  A kit's pieces are not interchangeable, so it is one unit. If its")
    print("  contents need to be findable, make the kit a LOCATION rather than")
    print("  exploding it into a pack — see docs/TECHNIQUES.md.")
    for sp, n, pq in sorted(kits, key=lambda r: -r[1]):
        print(f"   {n:>5} pcs   {(sp.part.name if sp.part else '')[:66]}")

if a.all and weak_bad:
    print(f"\nWEAK — 'set'/'lot'/'bag' may be a count or one assortment sold whole "
          f"({len(weak_bad)}):")
    for sp, n, pq in sorted(weak_bad, key=lambda r: -r[1])[:20]:
        print(f"   says {n:>5} / pq {pq:g}  {(sp.part.name if sp.part else '')[:62]}")

if divergent and not strong_bad:
    print(f"\n!! {len(divergent)} supplier part(s) will drop their pack on receive even "
          f"though the record\n   states it. Fix before receiving anything against them.")
    sys.exit(1)

if strong_bad:
    print(f"\n!! Receiving any of these books the WHOLE PACK PRICE against ONE piece,")
    print(f"   and the shelf then under-reports by a factor of the pack size. Set")
    print(f"   pack_quantity on the SUPPLIER part — never rename the part to say")
    print(f"   'pack of N', which makes the quantity column lie instead.")
    sys.exit(1)
print("\n  OK  no supplier part contradicts its own SKU or its own native pack value.")
