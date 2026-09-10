"""Price, place and receive PO-0164; retire the ad-hoc stock row; earmark for LRD."""
import os, sys, django
from decimal import Decimal
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.utils import timezone
from django.contrib.auth import get_user_model
from order.models import PurchaseOrder, PurchaseOrderLineItem, PurchaseOrderExtraLine
from order.status_codes import PurchaseOrderStatus
from stock.models import StockItem, StockLocation
from build.models import BuildItem
from part.models import Part

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
po = PurchaseOrder.objects.get(reference="PO-0164")
line = PurchaseOrderLineItem.objects.get(order=po)

# invoice 2583209A2026082923398500: 10 @ $0.97 = $9.70, shipping $8.90, total $18.60
PurchaseOrderLineItem.objects.filter(pk=line.pk).update(purchase_price=Decimal("0.97"))
if not PurchaseOrderExtraLine.objects.filter(order=po).exists():
    PurchaseOrderExtraLine.objects.create(order=po, description="Shipping - Global Standard Direct Line",
                                          quantity=1, price=Decimal("8.90"))
    print("   shipping added as an extra line: $8.90")
PurchaseOrder.objects.filter(pk=po.pk).update(
    notes="JLCPCB invoice 2583209A2026082923398500, 2026-09-02.\n"
          "Batch W2026082923398500, tracking YT2624400710357462.\n"
          "10 @ $0.97 = $9.70 merchandise, $8.90 shipping, **$18.60 grand total**.\n"
          "Landed cost **$1.86 per board**. Gerbers: git tag v1.1-run1.")

# retire the ad-hoc row before receiving, so the boards are not counted twice
pcb = Part.objects.get(name="HoT Info Orbs PCB v1.1")
for si in StockItem.objects.filter(part=pcb, purchase_order__isnull=True):
    n = BuildItem.objects.filter(stock_item=si).count()
    BuildItem.objects.filter(stock_item=si).delete()
    print(f"   retiring ad-hoc stock {si.pk} (qty {si.quantity:g}), released {n} allocation(s)")
    si.delete()

po.refresh_from_db()
if po.status != PurchaseOrderStatus.PLACED:
    po.place_order()
    po.refresh_from_db()
    print(f"   {po.reference} placed (status {po.status})")

loc = StockLocation.objects.get(pk=503)   # SLN/Florida Staging
line.refresh_from_db()
if line.received < line.quantity:
    po.receive_line_item(line, loc, line.quantity - line.received, user)
    print(f"   received {line.quantity:g} into {loc.pathstring}")
po.refresh_from_db(); line.refresh_from_db()
print(f"\n   {po.reference} status={po.status} received={line.received:g}/{line.quantity:g} total=${po.total_price}")
for si in StockItem.objects.filter(part=pcb):
    print(f"   stock {si.pk}: qty={si.quantity:g} @ {si.location.pathstring} price={si.purchase_price}")
