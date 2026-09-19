"""The 73 imageless active parts that DO have a SupplierPart, by supplier.

The 2026-08-30 run closed this bucket with evidence (Lakeshore clipart,
Tormach delisted, Amazon 16-of-17 404, McMaster out of policy) when it held 79.
It holds 73 now. Re-measuring rather than trusting a three-week-old closure,
because `closures-go-stale-with-inflow`: the bucket takes new rows every time a
PO is created, and a closure written against the rows examined then says
nothing about rows added since.

Also dumps the 5 link-only rows, which no run has ever named.

Read-only.
"""
import os
import sys
from collections import defaultdict
from urllib.parse import urlparse

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

NOIMG = Q(image="") | Q(image__isnull=True)
imageless = Part.objects.filter(active=True).filter(NOIMG).distinct()

by_supplier = defaultdict(list)
link_only = []

for p in imageless:
    sps = list(p.supplier_parts.all())
    if sps:
        for sp in sps:
            name = sp.supplier.name if sp.supplier else "?"
            by_supplier[name].append((p.pk, sp.SKU, p.name, sp.link or p.link or ""))
        continue
    link = (p.link or "").strip()
    if link:
        link_only.append((p.pk, urlparse(link).netloc, p.name, link))

print("=== imageless WITH a SupplierPart, by supplier ===")
for name, rows in sorted(by_supplier.items(), key=lambda kv: -len(kv[1])):
    print(f"\n-- {name}  ({len(rows)})")
    for pk, sku, pname, link in sorted(rows):
        print(f"  {pk}\t{sku[:34]:<34}\t{pname[:60]}")
        if link:
            print(f"      {link[:120]}")

print("\n=== imageless, link only, no SupplierPart ===")
for pk, host, pname, link in link_only:
    print(f"  {pk}\t{host}\t{pname[:70]}")
    print(f"      {link[:140]}")
