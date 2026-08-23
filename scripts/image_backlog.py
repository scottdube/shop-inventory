"""Report which parts lack a Part.image, grouped by whether a SKU can source one.

Queue A of the overnight enrich job kept being called "effectively spent" on the
strength of a headline number ("603 parts with no image"). That number hides the
only thing that matters: how many of them have a supplier SKU an image can
actually be fetched from, and from WHICH supplier. Amazon needs the driven-Chrome
path; Seeed/Mouser/Pololu/McMaster do not and never did.

So this prints the breakdown, not the total. Read-only.
"""
import os, sys, django
from collections import Counter
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from company.models import SupplierPart

total = Part.objects.count()
with_img = Part.objects.exclude(image="").exclude(image__isnull=True).count()
noimg = Part.objects.filter(image="") | Part.objects.filter(image__isnull=True)
noimg = noimg.distinct()

print(f"parts total      : {total}")
print(f"with image       : {with_img}")
print(f"WITHOUT image    : {noimg.count()}")

# Which of the imageless parts have a supplier part, and from whom.
by_supplier = Counter()
no_supplier = 0
rows = []
for p in noimg.prefetch_related("supplier_parts__supplier"):
    sps = list(p.supplier_parts.all())
    if not sps:
        no_supplier += 1
        continue
    for sp in sps:
        name = sp.supplier.name if sp.supplier else "?"
        by_supplier[name] += 1
    rows.append((p.pk, p.name[:60], [(sp.supplier.name if sp.supplier else "?", sp.SKU) for sp in sps]))

print(f"  of those, NO supplier part at all : {no_supplier}")
print(f"  of those, WITH a supplier part    : {len(rows)}")
print()
print("imageless parts by supplier (a part can appear under more than one):")
for name, n in by_supplier.most_common():
    print(f"  {n:5d}  {name}")

print()
print("=== workable rows (pk | name | supplier:SKU) ===")
for pk, name, sps in sorted(rows):
    joined = "  ".join(f"{s}:{k}" for s, k in sps)
    print(f"{pk}\t{name}\t{joined}")
