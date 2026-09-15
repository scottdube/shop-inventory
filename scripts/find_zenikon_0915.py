#!/usr/bin/env python3
"""Read-only: find the part/supplier-part behind PO-0172 (ZeniKon DP->Mini HDMI
cable) so the second order 111-2294439-2655441 of the SAME item reuses it
instead of creating a twin part."""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from company.models import SupplierPart  # noqa: E402
from part.models import Part  # noqa: E402

po = PurchaseOrder.objects.filter(supplier_reference="113-0032375-3000231").first()
print("PO:", po.reference, "| supplier:", po.supplier, "| pk:", po.pk)
for li in PurchaseOrderLineItem.objects.filter(order=po):
    sp = li.part
    print("  line qty=%s price=%s dest=%s" % (li.quantity, li.purchase_price, li.destination))
    print("  supplier_part pk=%s SKU=%s link=%s" % (sp.pk, sp.SKU, sp.link))
    print("  pack_quantity=%r native=%r" % (sp.pack_quantity, sp.pack_quantity_native))
    p = sp.part
    print("  part pk=%s name=%s active=%s" % (p.pk, p.name, p.active))
    print("  IPN=%s category=%s" % (p.IPN, p.category))
    print("  description=%s" % p.description)
    print("  keywords=%s" % p.keywords)

print("\n-- other rows mentioning zenikon --")
for p in Part.objects.filter(name__icontains="zenikon"):
    print("  part %s | %s | active=%s" % (p.pk, p.name, p.active))
for p in Part.objects.filter(description__icontains="zenikon"):
    print("  part(desc) %s | %s | active=%s" % (p.pk, p.name, p.active))
for sp in SupplierPart.objects.filter(SKU__icontains="zenikon"):
    print("  sp %s | %s | part=%s" % (sp.pk, sp.SKU, sp.part.pk))
