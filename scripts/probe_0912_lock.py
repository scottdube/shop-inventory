"""Read-only probe for Amazon order 113-0958514-9540223 (Hecfu 5/8in cam lock).

Queue C: check the PO does not already exist by supplier_reference, run the
four-way dedup (name / description 'orig:' / IPN / part-number token) required
before creating any part, and show where comparable cabinet hardware is filed
so the new part lands in the same tree rather than starting a third one.
"""
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402

REF = "113-0958514-9540223"
ASIN = "B09QD4S7BN"

print("-- PO idempotency (supplier_reference AND reference) --")
hits = PurchaseOrder.objects.filter(Q(supplier_reference=REF) | Q(reference=REF))
print(f"   {REF}: {hits.count()} existing PO(s)")
for po in hits:
    print(f"     {po.reference} {po.status} {po.supplier}")

print()
print("-- SupplierPart with this ASIN as SKU --")
for sp in SupplierPart.objects.filter(SKU__icontains=ASIN):
    print(f"   {sp.pk} {sp.supplier} {sp.SKU} -> part {sp.part.pk} {sp.part.name}")
else:
    pass
if not SupplierPart.objects.filter(SKU__icontains=ASIN).exists():
    print("   (none)")

print()
print("-- dedup: parts whose name/description/IPN/keywords mention a lock --")
q = (Q(name__icontains="cam lock") | Q(name__icontains="cabinet lock")
     | Q(description__icontains="cam lock") | Q(description__icontains="cabinet lock")
     | Q(name__icontains="lock") & Q(name__icontains="key")
     | Q(IPN__icontains=ASIN) | Q(description__icontains=ASIN)
     | Q(keywords__icontains="cam lock"))
for p in Part.objects.filter(q).order_by("pk"):
    cat = p.category.pathstring if p.category else "-"
    print(f"   pk {p.pk:5d} | {p.name[:50]:<50} | active={p.active} | {cat}")
if not Part.objects.filter(q).exists():
    print("   (no candidate duplicate)")

print()
print("-- broader: any part with 'lock' in the name (catch latch/lockwasher noise too) --")
for p in Part.objects.filter(name__icontains="lock").order_by("pk"):
    cat = p.category.pathstring if p.category else "-"
    print(f"   pk {p.pk:5d} | {p.name[:50]:<50} | active={p.active} | {cat}")

print()
print("-- candidate categories: anything hardware/fastener-ish --")
for c in PartCategory.objects.all().order_by("tree_id", "lft"):
    ps = c.pathstring
    if any(k in ps.lower() for k in ("hardware", "fasten", "mechanical", "misc")):
        print(f"   {c.pk:4d} | {ps:<60} | parts={c.parts.count()}")

print()
print("-- Amazon company row --")
for co in Company.objects.filter(name__icontains="amazon"):
    print(f"   pk {co.pk} {co.name} is_supplier={co.is_supplier}")
