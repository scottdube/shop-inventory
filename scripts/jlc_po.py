"""Draft the JLCPCB purchase order for the v1.1 run. Price filled in separately."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from company.models import Company, SupplierPart
from order.models import PurchaseOrder, PurchaseOrderLineItem
from part.models import Part

jlc = Company.objects.get(pk=19)
pcb = Part.objects.get(name="HoT Info Orbs PCB v1.1")

sp, made = SupplierPart.objects.get_or_create(
    part=pcb, supplier=jlc,
    defaults=dict(SKU="HOT-INFO-ORBS-V1.1", pack_quantity="1",
                  note="2-layer, 198.8 x 28.5mm, 1.6mm. Gerbers: git tag v1.1-run1"))
print(f"   supplier part #{sp.pk} {'created' if made else 'exists'}  SKU={sp.SKU}")

po = PurchaseOrder.objects.filter(supplier=jlc, description__icontains="Info Orbs").first()
if not po:
    po = PurchaseOrder.objects.create(
        supplier=jlc,
        description="HoT Info Orbs PCB v1.1 - first production run"[:250])
    print(f"   {po.reference} created (draft)")
else:
    print(f"   {po.reference} already exists")

line = PurchaseOrderLineItem.objects.filter(order=po, part=sp).first()
if not line:
    line = PurchaseOrderLineItem.objects.create(order=po, part=sp, quantity=10)
    print(f"   line added: 10x {pcb.name}")
print(f"\n   {po.reference}  status={po.status}  price on line = {line.purchase_price}")
print(f"   /web/purchasing/purchase-order/{po.pk}")
