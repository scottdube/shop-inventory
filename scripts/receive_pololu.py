"""First real receive: the Pololu PO, split across two destinations.

ToF sensors -> the red ongoing-project bin (Project Bins); jumper wires ->
B3-R7C1 (Prototyping boards, "with the rest of the breadboard stuff").
Uses InvenTree's own receive_line_item so pack conversion and per-device
purchase_price follow the house convention (order/models.py).
"""
import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from company.models import Company
from order.models import PurchaseOrder
from stock.models import StockLocation, StockItem

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
pololu = Company.objects.get(name__iexact="Pololu")
po = PurchaseOrder.objects.filter(supplier=pololu).order_by("-pk").first()
if not po:
    sys.exit("no Pololu PO found")
print(f"PO: {po.reference}  supplier_ref={po.supplier_reference}  status={po.status}\n")

bins = StockLocation.objects.filter(name__icontains="Project Bin").first()
drawer = StockLocation.objects.filter(name="B3-R7C1").first()
print(f"destinations: ToF -> {bins.pathstring if bins else 'MISSING'}")
print(f"              jumpers -> {drawer.pathstring if drawer else 'MISSING'}\n")

TOF = ("tof", "vl53", "distance", "lidar", "range")
JUMP = ("jumper", "wire", "cable", "premium")

for line in po.lines.all():
    part = line.part  # SupplierPart
    name = (part.part.name if part else str(line)) or ""
    low = name.lower()
    if any(t in low for t in TOF):
        dest, tag = bins, "bin"
    elif any(t in low for t in JUMP):
        dest, tag = drawer, "drawer"
    else:
        print(f"  ?? UNMAPPED, left unreceived: {name[:60]}")
        continue
    already = float(line.received or 0)
    qty = float(line.quantity) - already
    if qty <= 0:
        print(f"  already received: {name[:56]}")
        continue
    print(f"  receive {qty:g} x {name[:52]:<52} -> {tag} ({dest.name})")
    if a.commit:
        po.receive_line_item(line, dest, qty, user)

if a.commit:
    po.refresh_from_db()
    print(f"\nPO after: status={po.status_text if hasattr(po,'status_text') else po.status}")
    print("\nstock created:")
    for si in StockItem.objects.filter(purchase_order=po):
        print(f"  {si.quantity:g} x {si.part.name[:48]:<48} @ {si.location.name if si.location else '-'}  price={si.purchase_price}")
print("\n" + ("WROTE" if a.commit else "DRY RUN — add --commit"))
