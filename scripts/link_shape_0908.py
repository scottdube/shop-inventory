"""Measure the SHAPE of every stored link. Read-only. 2026-09-08.

Tonight's queue A probe found that the remaining "reachable" imageless parts are
reachable only on paper: their stored link is a vendor SEARCH url, not a product
url. Measured live tonight:

  Lakeshore  search.aspx?find=10-SPTRMLB  -> 2 results (fuzzy), 0 product images
  Lakeshore  search.aspx?find=1/4-SPTRMLB -> 9 results (fuzzy), 0 product images
  Tormach    catalogsearch?q=34444        -> 1 result: "USB Bulkhead Port
                                            Assembly" (part is a 15L LATHE)
  Tormach    catalogsearch?q=39044        -> 4 whole-mill configurators
                                            (part is an ENCLOSURE KIT)

Two of those Tormach pages did NOT show the "No exact results found" banner, so
the banner cannot be used as the guard either. A search URL therefore resolves
to zero, many, or the WRONG product, and any harvester that trusts it will
attach a confidently wrong photo.

This script quantifies the shape across all stored links so the finding is a
number rather than four anecdotes. It writes nothing.
"""
import os
import re
import sys
from collections import Counter
from urllib.parse import urlparse

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from part.models import Part  # noqa: E402

# A link is SEARCH-SHAPED if the path or query says "find me something",
# rather than naming one product.
SEARCH_PAT = re.compile(
    r"(/search|/catalogsearch|/products/result|[?&](q|s|find|keywords|search)=)",
    re.I,
)


def shape(url):
    if not url:
        return "empty"
    if SEARCH_PAT.search(url):
        return "SEARCH (false handle)"
    if urlparse(url).netloc.endswith("github.com"):
        return "github (project, not a product)"
    return "product-shaped"


print("== SupplierPart.link shape, by supplier ==")
rows = SupplierPart.objects.select_related("supplier", "part")
per_sup = {}
for sp in rows:
    sup = sp.supplier.name if sp.supplier else "?"
    per_sup.setdefault(sup, Counter())[shape(sp.link)] += 1
for sup in sorted(per_sup, key=lambda s: -sum(per_sup[s].values())):
    c = per_sup[sup]
    bits = "  ".join(f"{k}={v}" for k, v in c.most_common())
    print(f"  {sup:<24} {sum(c.values()):4d}   {bits}")

print()
print("== overall ==")
tot = Counter()
for c in per_sup.values():
    tot.update(c)
for k, v in tot.most_common():
    print(f"  {k:<34} {v}")

print()
print("== the specific harm: IMAGELESS active parts whose only handle is a SEARCH url ==")
n = 0
for p in Part.objects.filter(active=True, image=""):
    urls = [sp.link for sp in SupplierPart.objects.filter(part=p)] + [p.link]
    urls = [u for u in urls if u]
    if not urls:
        continue
    if all(shape(u) == "SEARCH (false handle)" for u in urls):
        n += 1
        print(f"  pk {p.pk:5d} | {p.name[:46]:<46} | {urls[0][:64]}")
print(f"  ({n} parts look reachable in queue A and are not)")

print()
print("== product-shaped links on imageless active parts (the REAL remaining pool) ==")
m = 0
for p in Part.objects.filter(active=True, image=""):
    for sp in SupplierPart.objects.filter(part=p):
        if shape(sp.link) == "product-shaped":
            m += 1
            sup = sp.supplier.name if sp.supplier else "?"
            print(f"  pk {p.pk:5d} | {p.name[:40]:<40} | {sup:<16} | {sp.link[:58]}")
print(f"  ({m} rows)")
