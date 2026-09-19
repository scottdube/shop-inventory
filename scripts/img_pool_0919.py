"""Measure tonight's queue-A pool, read-only.

The 09-17/09-18 runs opened a route that the older "queue A is finished"
rulings did not have: parts with NO SupplierPart and NO link can still carry
their provenance in PROSE in the description ("via Amazon; last ordered
2026-07-09"), and the recorded date turns an Amazon order-history search from
a guess into a confirmable match.

09-18 measured that prose pool at 18 and took 12. This re-measures rather than
assuming, and splits what is left by the vendor named in the prose, because an
eBay provenance line needs a different instrument than an Amazon one.
"""
import os
import re
import sys
from collections import Counter

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

NOIMG = Q(image="") | Q(image__isnull=True)

active = Part.objects.filter(active=True)
total = active.count()
imageless = active.filter(NOIMG).distinct()

print(f"active parts            : {total}")
print(f"  with image            : {total - imageless.count()}")
print(f"  imageless             : {imageless.count()}")
print()

VIA = re.compile(r"\bvia\s+([A-Za-z][A-Za-z0-9 .&'-]{1,24})", re.I)
DATE = re.compile(r"(?:last ordered|ordered)\s*:?\s*(\d{4}-\d{2}-\d{2})", re.I)

buckets = Counter()
prose_rows = []

for p in imageless:
    has_sp = p.supplier_parts.exists()
    link = (p.link or "").strip()
    desc = p.description or ""
    notes = p.notes or ""
    blob = f"{desc}\n{notes}"
    m_via = VIA.search(blob)
    m_date = DATE.search(blob)

    if has_sp:
        buckets["has SupplierPart"] += 1
    elif link:
        buckets["link only"] += 1
    elif m_via or m_date:
        vendor = (m_via.group(1).strip() if m_via else "?").split(";")[0].strip()
        buckets[f"prose: {vendor}"] += 1
        prose_rows.append((p.pk, vendor, m_date.group(1) if m_date else "", p.name, desc))
    else:
        buckets["no handle at all"] += 1

print("=== imageless, by handle ===")
for k, v in buckets.most_common():
    print(f"{v:>5}  {k}")

print("\n=== prose-provenance rows (the live pool) ===")
for pk, vendor, date, name, desc in sorted(prose_rows, key=lambda r: (r[1].lower(), r[0])):
    print(f"\n{pk}\t[{vendor}] {date}\t{name[:90]}")
    print(f"      {desc[:400]}")
