"""Overnight 2026-09-25: queue A's "no handle" rows may still carry a handle IN THE NAME.

The 09-22 TRAPS entry counted 435 imageless parts with no link and no supplier
part as "no handle of any kind". The 09-24 entry then established that a
SKU-less part can pass the image identity guard on maker + model read off the
record. A maker part number embedded in the part name (e.g. #1237
"Stontronics DSA-13PFC-05") is exactly such a handle, and no run has bucketed
by it. This lists active, imageless, no-link, no-supplier-part rows whose name
carries a part-number-shaped token, so they can be judged one by one.

Read-only.
"""
import os
import re
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from part.models import Part  # noqa: E402

NOIMG = Q(image="") | Q(image__isnull=True)
NOLINK = Q(link="") | Q(link__isnull=True)

# Tokens that mix letters and digits but are ratings, sizes or generic
# connector names rather than a maker's part number.
RATING = re.compile(
    r"^(\d+(\.\d+)?(mm|cm|m|in|ft|v|vdc|vac|a|ma|w|kw|pin|p|pcs|pc|uf|nf|pf|k|r|ohm|awg|mhz|khz|hz|mah|gb|mb|rpm|nm|g|kg|s|ms|x)+"
    r"|\d+x\d+.*|m\d+(x[\d.]+)?|cat\d+e?|rj\d+|\d+p\d+c|to-?\d+|sot-?\d+|dip-?\d+|soic-?\d+|\d+(\.\d+)?-\d+(\.\d+)?[a-z]*"
    r"|gen\d|v\d+(\.\d+)?|\d+s|\d+d|\d+th|\d+nd|\d+rd|\d+st|usb\d?|i2c|\d+bit|\d+-way|\d+-pin|\d+-position)$",
    re.I,
)
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-_/.]{3,}[A-Za-z0-9]")


def pn_tokens(name):
    out = []
    for t in TOKEN.findall(name or ""):
        if not (re.search(r"[A-Za-z]", t) and re.search(r"\d", t)):
            continue
        if RATING.match(t):
            continue
        out.append(t)
    return out


sp_parts = set(SupplierPart.objects.values_list("part_id", flat=True))
pool = Part.objects.filter(NOIMG, NOLINK, active=True).exclude(pk__in=sp_parts).order_by("pk")
print(f"imageless active, no link, no supplier part: {pool.count()}")

hits = []
for p in pool:
    toks = pn_tokens(p.name)
    if toks:
        hits.append((p, toks))

print(f"with a part-number-shaped token in the name: {len(hits)}\n")
for p, toks in hits:
    cat = p.category.pathstring if p.category else "-"
    print(f"part={p.pk:<5} tok={','.join(toks):<28} | {p.name[:80]} | {cat[:40]}")
