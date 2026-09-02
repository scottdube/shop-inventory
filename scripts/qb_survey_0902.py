"""Queue B survey — what already exists for the un-imported Tormach/MSC orders.

Read-only. Answers, per candidate SKU from the order emails:
  - is there a SupplierPart with this SKU (and under which supplier)?
  - which Part does it point at, and does that Part already carry a cost?
  - is there a PO carrying the vendor order number in supplier_reference?

The point is to find out whether queue B's remaining work is "attach a price to
a part that exists" or "the part is not in the system at all", BEFORE writing
anything. Cost mining is only allowed to add cost, never to overwrite one.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from part.models import Part  # noqa: E402

# (vendor, sku, description as it appears in the order email)
CANDIDATES = [
    ("Tormach", "51240", "USB Camera for PathPilot-Controlled Machines"),
    ("Tormach", "51208", "PathPilot Keyboard Shortcuts Mousepad"),
    ("Tormach", "31280", "Face Mill - 38 mm"),
    ("Tormach", "37237", "Carbide Insert for Aluminum and Plastic - Face & End Mills 10-Pack"),
    ("Tormach", "39676", "BT30 Tool Holder, Face Mill Arbor 1/2 in, 35mm"),
    ("Tormach", "37553", "Pull Stud, BT30 45-Degree"),
    ("Tormach", "39670", "BT30 Tool Holder, End Mill 1/4 in, 50mm"),
    ("Tormach", "39668", "BT30 Tool Holder, End Mill 1/8 in, 50mm"),
    ("Tormach", "39671", "BT30 Tool Holder, End Mill 3/8 in, 50mm"),
    ("Tormach", "39673", "BT30 Tool Holder, Drill Chuck 8mm, 80mm"),
    ("MSC", "00447474", 'NO.90X 1/2-1-1/8" 4JT TAPMATIC TAPPING UNIT'),
]

ORDERS = ["3000048956", "3000053997", "225102790", "3000048323", "3000059655", "3000059656"]

print("=== suppliers matching Tormach / MSC ===")
for c in Company.objects.filter(is_supplier=True):
    n = c.name.lower()
    if "tormach" in n or "msc" in n:
        print(f"  pk={c.pk:4d}  {c.name!r}  supplier_parts={c.supplied_parts.count()}")

print("\n=== candidate SKUs ===")
for vendor, sku, desc in CANDIDATES:
    sps = list(SupplierPart.objects.filter(SKU=sku))
    if not sps:
        # SKU may be stored zero-stripped or with vendor prefix; widen once.
        sps = list(SupplierPart.objects.filter(SKU__icontains=sku.lstrip("0")))
    if not sps:
        print(f"  {vendor:8s} {sku:10s} NO SupplierPart      | {desc[:52]}")
        continue
    for sp in sps:
        p = sp.part
        cost = None
        try:
            cost = sp.purchase_price
        except Exception:
            pass
        print(f"  {vendor:8s} {sku:10s} sp={sp.pk:4d} part={p.pk:4d} pack={sp.pack_quantity!r} "
              f"sp_price={cost} | {p.name[:44]}")

print("\n=== parts whose name/description hints at these items (dedup check) ===")
for token in ["Tapmatic", "Face Mill", "Pull Stud", "Drill Chuck", "USB Camera", "Mousepad"]:
    hits = Part.objects.filter(name__icontains=token) | Part.objects.filter(description__icontains=token)
    hits = hits.distinct()
    print(f"  {token!r}: {hits.count()}")
    for p in hits[:8]:
        print(f"      pk={p.pk:4d} {p.name[:56]!r} cat={p.category}")

print("\n=== vendor order numbers already on a PO ===")
for o in ORDERS:
    hits = (PurchaseOrder.objects.filter(supplier_reference=o) |
            PurchaseOrder.objects.filter(reference=o)).distinct()
    if hits.exists():
        for po in hits:
            print(f"  EXISTS {o} -> {po.reference} status={po.get_status_display()} lines={po.lines.count()}")
    else:
        print(f"  absent {o}")
