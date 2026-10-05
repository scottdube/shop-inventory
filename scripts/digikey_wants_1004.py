"""Read-only: anything Scott meant to buy from DigiKey? Open POs to DigiKey, DigiKey
supplier parts, and parts/stock whose notes mention DigiKey alongside order/buy."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.models import Q
from company.models import Company, SupplierPart
from order.models import PurchaseOrder
from part.models import Part

dk = Company.objects.filter(Q(name__icontains="digi") )
print("== companies:", [(c.pk, c.name) for c in dk])
print("== ALL POs to those companies (any status)")
for po in PurchaseOrder.objects.filter(supplier__in=dk).order_by("-creation_date"):
    print(f"  {po.reference} status={po.get_status_display()} created={po.creation_date} sref={po.supplier_reference} | {po.description[:60]}")
    for li in po.lines.all():
        print(f"    {li.part} qty={li.quantity} recv={li.received}")
print("== DigiKey supplier parts")
for sp in SupplierPart.objects.filter(supplier__in=dk):
    print(f"  sp={sp.pk} part#{sp.part_id} {sp.SKU} | {sp.part.name[:60]} stock={sp.part.total_stock}")
print("== parts whose notes/description mention digikey (all printed)")
for p in Part.objects.filter(Q(notes__icontains="digikey") | Q(notes__icontains="digi-key")
                             | Q(description__icontains="digikey") | Q(description__icontains="digi-key")):
    import re
    txt = (p.notes or "") + " " + (p.description or "")
    m = re.search(r".{0,90}digi-?key.{0,120}", txt, re.I | re.S)
    print(f"  part#{p.pk} stock={p.total_stock} {p.name[:50]} :: {m.group(0).replace(chr(10),' ') if m else ''}")
