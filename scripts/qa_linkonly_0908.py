"""Queue A probe, 2026-09-08. Read-only.

The 2026-09-01 closure and the open decision item `queue-a-exhausted` are both
statements about ONE set: imageless active parts that have a SupplierPart (73
then, 69 now). state_0908 counts a SECOND, smaller bucket separately -- 5
imageless active parts with NO SupplierPart but a non-empty Part.link -- and
nothing in the journal says those were ever tried. A closure over set X is not
evidence about set Y, so dump Y before calling the queue empty.

Also breaks the 69 down by supplier and reports whether each carries a
SupplierPart.link, so the closure can be re-checked cheaply if it needs to be.
"""
import os
import sys
from collections import Counter

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from part.models import Part  # noqa: E402

imageless = Part.objects.filter(active=True, image="")

print("== bucket Y: imageless, NO SupplierPart, HAS Part.link ==")
n = 0
for p in imageless.exclude(link="").exclude(link__isnull=True):
    if SupplierPart.objects.filter(part=p).exists():
        continue
    n += 1
    print(f"  pk {p.pk:5d} | {p.name[:50]}")
    print(f"          cat={p.category.pathstring if p.category else '-'}")
    print(f"          link={p.link}")
    print(f"          created={p.creation_date}  IPN={p.IPN!r}")
print(f"  ({n} parts)")

print()
print("== bucket X: imageless WITH SupplierPart -- supplier histogram ==")
hist = Counter()
nolink = Counter()
for p in imageless:
    sps = list(SupplierPart.objects.filter(part=p))
    if not sps:
        continue
    for sp in sps:
        sup = sp.supplier.name if sp.supplier else "?"
        hist[sup] += 1
        if not (sp.link or p.link):
            nolink[sup] += 1
for sup, c in hist.most_common():
    print(f"  {sup:<22} {c:4d}   of which no link at all: {nolink[sup]}")

print()
print("== bucket X detail: those that DO carry a fetchable link ==")
m = 0
for p in imageless:
    for sp in SupplierPart.objects.filter(part=p):
        url = sp.link or p.link
        if not url:
            continue
        m += 1
        sup = sp.supplier.name if sp.supplier else "?"
        print(f"  pk {p.pk:5d} | {p.name[:42]:<42} | {sup}:{sp.SKU}")
        print(f"          {url}")
print(f"  ({m} supplier-part rows with a link)")

print()
print("== the 37 empty-keyword parts (all, incl. inactive) ==")
EMPTY_KW = Q(keywords__isnull=True) | Q(keywords="")
for p in Part.objects.filter(EMPTY_KW).order_by("pk"):
    print(f"  pk {p.pk:5d} | active={str(p.active):<5} | {p.name[:56]}")
