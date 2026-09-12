"""Queue A: the imageless active parts whose only handle is Part.link.

The 2026-09-01 closure covered parts reachable through a SupplierPart. The
link-only bucket was counted but never worked, and the 'search-urls-are-false-
handles' ruling applies to SupplierPart.link, not to these. Read-only: print
each link so a real product page can be told from a vendor search URL before
anything is fetched.
"""
import os
import sys
from urllib.parse import urlparse

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from part.models import Part  # noqa: E402

SEARCHY = ("?s=", "search", "/s?", "q=", "keyword")

print("-- imageless active parts with Part.link and NO SupplierPart --")
n = 0
for p in Part.objects.filter(active=True, image="").order_by("pk"):
    # null-safe: .exclude(link="") lets NULLs through, which is the standing
    # null-blind trap on this install — test the value, not the empty string.
    if not p.link:
        continue
    if SupplierPart.objects.filter(part=p).exists():
        continue
    n += 1
    host = urlparse(p.link).netloc
    flag = "SEARCH-URL?" if any(k in p.link.lower() for k in SEARCHY) else "product?"
    print(f"   pk {p.pk:5d} | {p.name[:44]:<44} | {host:<24} | {flag}")
    print(f"           {p.link}")
print(f"   ({n} parts)")

print()
print("-- imageless active parts with a SupplierPart, grouped by supplier --")
from collections import Counter  # noqa: E402
c = Counter()
for p in Part.objects.filter(active=True, image=""):
    for sp in SupplierPart.objects.filter(part=p):
        c[sp.supplier.name if sp.supplier else "?"] += 1
for name, k in c.most_common():
    print(f"   {name:<22} {k}")
