"""Read-only second pass: split the pack FLAGs into kits and true multipacks.

pack_sweep_0913.py flagged 154 supplier parts whose title carries a count > 1
while the stored pack size is 1. Most of those are NOT defects, and printing
them as one list of 154 is an undecidable pile rather than a finding:

    "ER20 Collet Set 1/16-1/2in, 10pc"      <- one SET, ten different collets
    "No.10 18 Pcs Hss Keyway Broach Sets"   <- one boxed set
    "Vanjua 4 Pack 90 Degree USB-C Adapter" <- four identical adapters

The first two are correct at pack_quantity 1: the purchase unit IS the set, and
its members are not interchangeable, so booking 10 of anything would be wrong.
Only the third class — N identical interchangeable units bought as one line —
is the importer defect that mis-prices a receipt.

So this classifies rather than lists. A title carrying set/kit/assortment
vocabulary is a KIT; the rest are MULTIPACK candidates, printed in full because
that is the list a human can actually rule on. The split is a heuristic on
vendor prose, so both buckets are reported with counts and the KIT bucket is
summarised, not hidden.

Writes nothing.
"""
import os
import re
import sys
from decimal import Decimal, InvalidOperation

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402

PACK_RE = [
    re.compile(r"(?<![\d.])(\d{1,4})\s*[- ]?\s*(?:pack|packs|pcs|pieces|piece|count|ct)\b", re.I),
    re.compile(r"pack\s+of\s+(\d{1,4})\b", re.I),
    re.compile(r"(?<![\d.])(\d{1,4})\s*[- ]?\s*p[cs]s?\b", re.I),
]

# Vocabulary that means "the purchase unit is one assembled/boxed collection
# whose members differ" — pack_quantity 1 is correct for all of these.
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


kits, multi = [], []

for sp in SupplierPart.objects.select_related("part", "supplier").order_by("pk"):
    native = as_dec(sp.pack_quantity_native)
    if native is not None and native != 1:
        continue
    title = " | ".join(
        str(x) for x in (sp.part.name, sp.part.description, sp.note, sp.SKU) if x
    )
    n = pack_from_title(title)
    if not n:
        continue
    (kits if KIT_RE.search(title) else multi).append((sp, n, title))

print(f"pack FLAGs total        : {len(kits) + len(multi)}")
print(f"  KIT      (pack 1 is correct — one boxed set, members differ) : {len(kits)}")
print(f"  MULTIPACK candidate (N identical units, pack 1 mis-prices)  : {len(multi)}")

print("\n-- KIT bucket, summarised (no action; purchase unit is the set) --")
for sp, n, _t in kits:
    print(f"   SP {sp.pk:4d} | {n:4d} in set | #{sp.part.pk} {sp.part.name[:58]}")

print("\n-- MULTIPACK candidates — each one mis-prices its receipt if real --")
if not multi:
    print("   none")
for sp, n, title in multi:
    print(f"   SP {sp.pk:4d} | title says {n:4d} | {sp.supplier.name} {sp.SKU}")
    print(f"            part #{sp.part.pk} {sp.part.name[:64]}")
    print(f"            {title[len(sp.part.name):][:150]}")
