"""Read-only: print the EXACT matched substring behind each of the 23 PIECES
candidates, so a regex artifact cannot be mistaken for a finding.

The open item `pack-hygiene-as-standing-queue` records that 2 of 31 flags in the
2026-09-05 sweep were artifacts — a digit read out of an ASIN (B01983R7PK ->
"7PK") and out of a chip name ("ESP32C6 Pack" -> "6 Pack"). That item's own
conclusion is that an automated writer needs the evidence dump in the loop, not
the audit's verdict. This is that dump for tonight's candidates: the matched
text, with surrounding context and which field it came from.

Also prints where the count came from, because the fields differ in authority:
a count in the part NAME or in the `orig:` vendor title is the vendor's own
statement, while a count appearing only in a SKU string is the shape that
produced both known artifacts.
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

from company.models import SupplierPart  # noqa: E402
from stock.models import StockItem        # noqa: E402

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


def as_dec(v):
    if v in (None, ""):
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


def matches(text):
    """(n, matched_text, context) for every pack hit in one field."""
    out = []
    for rx in PACK_RE:
        for m in rx.finditer(text or ""):
            try:
                n = int(m.group(1))
            except ValueError:
                continue
            if 1 < n <= 5000:
                a, b = max(0, m.start() - 28), min(len(text), m.end() + 28)
                out.append((n, m.group(0), text[a:b].replace("\n", " ")))
    return out


rows = 0
for sp in SupplierPart.objects.select_related("part", "supplier").order_by("pk"):
    native = as_dec(sp.pack_quantity_native)
    if native is not None and native != 1:
        continue

    fields = {
        "part.name": sp.part.name,
        "part.description": sp.part.description,
        "sp.note": sp.note,
        "sp.SKU": sp.SKU,
    }
    joined = " | ".join(str(v) for v in fields.values() if v)
    if KIT_RE.search(joined):
        continue
    if not any(matches(v) for v in fields.values()):
        continue

    qty = StockItem.objects.filter(part=sp.part).aggregate(q=Sum("quantity"))["q"]
    if qty is None or qty <= 1:
        continue  # only the PIECES bucket is up for a write

    rows += 1
    print(f"\nSP {sp.pk} | {sp.supplier.name} {sp.SKU} | part #{sp.part.pk} {sp.part.name[:56]}")
    print(f"   stock {qty} | pack_quantity_native {native}")
    for fname, val in fields.items():
        for n, hit, ctx in matches(val):
            authority = "SKU-ONLY (artifact shape)" if fname == "sp.SKU" else "vendor statement"
            print(f"   {fname:16s} n={n:<4d} matched {hit!r:14s} [{authority}]")
            print(f"                    ...{ctx}...")

print(f"\nPIECES candidates dumped: {rows}")
