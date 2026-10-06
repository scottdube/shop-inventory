"""Read-only: what does InvenTree already hold for Xoomspeed / the Tormach probe?"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.models import Q
from company.models import Company, SupplierPart
from order.models import PurchaseOrder
from part.models import Part, PartCategory
from stock.models import StockItem, StockLocation

print("## companies")
for c in Company.objects.filter(Q(name__icontains="xoom") | Q(name__icontains="loomes") | Q(name__icontains="tormach")):
    print(f"  #{c.pk} {c.name} supplier={c.is_supplier} mfr={c.is_manufacturer}")
print("## parts")
q = (Q(name__icontains="xoom") | Q(description__icontains="xoom") | Q(name__icontains="probe") |
     Q(name__icontains="spector") | Q(name__icontains="usb i/o") | Q(name__icontains="usb io") |
     Q(name__icontains="usbio") | Q(name__icontains="tool setter") | Q(name__icontains="ets") |
     Q(keywords__icontains="xoom") | Q(keywords__icontains="probe"))
for p in Part.objects.filter(q).order_by("pk"):
    st = sum(s.quantity for s in StockItem.objects.filter(part=p))
    print(f"  #{p.pk} active={p.active} [{p.category.pathstring if p.category else '-'}] {p.name!r} stock={st}")
print("## POs")
for po in PurchaseOrder.objects.filter(Q(supplier__name__icontains="xoom") | Q(supplier_reference__in=["1298","1374","#1298","#1374"])):
    print(f"  {po.reference} {po.supplier.name} {po.supplier_reference} status={po.status}")
print("## categories mentioning tooling/equipment/machine")
for c in PartCategory.objects.filter(Q(pathstring__icontains="tooling") | Q(pathstring__icontains="equipment") | Q(pathstring__icontains="machine") | Q(pathstring__icontains="accessor")).order_by("pathstring"):
    print(f"  #{c.pk} {c.pathstring}  parts={c.parts.count()}")
print("## locations mentioning mill / tormach / 1100 / cnc")
for l in StockLocation.objects.filter(Q(pathstring__icontains="mill") | Q(pathstring__icontains="tormach") | Q(pathstring__icontains="1100") | Q(pathstring__icontains="cnc")).order_by("pathstring"):
    print(f"  #{l.pk} {l.pathstring}  items={l.stock_items.count()}")
