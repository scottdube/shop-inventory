"""Read-only, 12:40 sweep 2026-09-29: how are Haas Tooling orders and parts
recorded (the first probe found NO PO under company #5 'Haas Tooling').
"""
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from part.models import PartCategory  # noqa: E402

haas_sps = SupplierPart.objects.filter(supplier__name__icontains="haas").order_by("-pk")
print(f"Haas supplier parts: {haas_sps.count()}")
for sp in haas_sps[:12]:
    p = sp.part
    print(f"  sp #{sp.pk} SKU={sp.SKU} pack={sp.pack_quantity} -> part #{p.pk} {p.name!r} "
          f"cat={p.category.pathstring if p.category else None}")
    print(f"      desc={p.description[:90]!r} kw={(p.keywords or '')[:80]!r}")

pos = PurchaseOrder.objects.filter(
    Q(lines__part__supplier__name__icontains="haas") | Q(notes__icontains="haas")
    | Q(description__icontains="haas")).distinct().order_by("-pk")
print(f"\nPOs touching Haas: {pos.count()}")
for po in pos[:5]:
    print(f"  {po.reference} supplier={po.supplier.name} sref={po.supplier_reference} "
          f"status={po.status} desc={po.description[:70]!r}")
    print("    notes:", (po.notes or "")[:500].replace("\n", " | "))
    for li in po.lines.all():
        print(f"    line {li.part.SKU} qty {li.quantity} @ {li.purchase_price} "
              f"notes={(li.notes or '')[:200]!r}")

print("\nTooling categories:")
for c in PartCategory.objects.filter(pathstring__startswith="Tooling"):
    print(f"  {c.pk} {c.pathstring} ({c.parts.count()})")
