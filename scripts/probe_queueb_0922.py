"""Queue B probe — what already exists for the 3 un-imported tooling orders.

Read-only. Answers the three questions that have to be answered BEFORE any
write, in one ssh round trip:

  1. Does a PO already carry these vendor order numbers? (supplier_reference is
     the idempotency key; normalized comparison, same as po_check.py.)
  2. Do the supplier Companies exist, and what are their pks?
  3. For each order-line SKU: is there already a SupplierPart with that SKU, and
     is there a Part whose name / description / IPN carries the SKU token?

Question 3 is the dedup rule from the task file: a vendor title never matches a
canonicalized part name, so check the SKU token in all four places instead.
"""
import os
import re
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from part.models import Part  # noqa: E402


def _norm(s):
    return re.sub(r"[^A-Za-z0-9]", "", s or "").lower()


ORDERS = ["3000048956", "3000053997", "225102790",
          "3000048323", "3000059655", "3000059656"]

# SKU -> the vendor's own line description, for the report only.
SKUS = {
    "51240": "USB Camera for PathPilot-Controlled Machines",
    "51208": "PathPilot Keyboard Shortcuts Mousepad",
    "31280": "Face Mill - 38 mm",
    "37237": "Carbide Insert for Aluminum and Plastic - Face & End Mills 10-Pack",
    "39676": "BT30 Tool Holder, Face Mill Arbor 1/2 in, 35mm",
    "37553": "Pull Stud, BT30 45-Degree",
    "39670": "BT30 Tool Holder, End Mill 1/4 in, 50mm",
    "39668": "BT30 Tool Holder, End Mill 1/8 in, 50mm",
    "39671": "BT30 Tool Holder, End Mill 3/8 in, 50mm",
    "39673": "BT30 Tool Holder, Drill Chuck 8mm, 80mm",
    "00447474": "NO.90X 1/2-1-1/8in 4JT TAPMATIC TAPPING UNIT",
}

print("=== POs ===")
index = {}
for po in PurchaseOrder.objects.all():
    for key in (_norm(po.supplier_reference), _norm(po.reference)):
        if key:
            index.setdefault(key, []).append(po)
for o in ORDERS:
    hits = index.get(_norm(o), [])
    if hits:
        for po in hits:
            print(f"EXISTS  {o} -> {po.reference} supplier_ref={po.supplier_reference!r} "
                  f"{po.get_status_display()} {po.supplier} lines={po.lines.count()}")
    else:
        print(f"absent  {o}")

print("\n=== companies ===")
for term in ("tormach", "msc"):
    for c in Company.objects.filter(name__icontains=term):
        print(f"pk={c.pk:4d} {c.name!r} supplier={c.is_supplier} "
              f"suppliers_parts={c.supplied_parts.count()}")

print("\n=== SKUs ===")
for sku, desc in SKUS.items():
    bare = sku.lstrip("0")
    print(f"\n-- {sku}  {desc}")
    sps = SupplierPart.objects.filter(SKU__icontains=bare)
    for sp in sps:
        print(f"   SupplierPart pk={sp.pk} SKU={sp.SKU!r} supplier={sp.supplier} "
              f"part=#{sp.part.pk} {sp.part.name!r} pack={sp.pack_quantity!r}")
    q = (Part.objects.filter(name__icontains=bare)
         | Part.objects.filter(description__icontains=bare)
         | Part.objects.filter(IPN__icontains=bare)
         | Part.objects.filter(keywords__icontains=bare))
    for p in q.distinct():
        print(f"   Part #{p.pk} {p.name!r} active={p.active} IPN={p.IPN!r} "
              f"cat={p.category} img={bool(p.image)}")
    if not sps and not q.exists():
        print("   (no match on the SKU token)")

print("\n=== word probe on the distinctive terms ===")
for term in ("tapmatic", "face mill", "pull stud", "drill chuck", "usb camera", "mousepad"):
    hits = (Part.objects.filter(name__icontains=term)
            | Part.objects.filter(description__icontains=term)).distinct()
    print(f"\n-- {term!r}: {hits.count()}")
    for p in hits[:12]:
        print(f"   #{p.pk} {p.name!r} active={p.active} cat={p.category}")
