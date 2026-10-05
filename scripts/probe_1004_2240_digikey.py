"""Read-only probe for DigiKey order 102025753 (2026-10-04): supplier company,
duplicates for both lines across name/description/IPN/keywords/SKU/MPN, and the
categories existing relays and axial resistors live in. Prints every hit."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.models import Q
from company.models import Company, SupplierPart, ManufacturerPart
from order.models import PurchaseOrder
from part.models import Part, PartCategory

print("== companies matching digi")
for c in Company.objects.filter(name__icontains="digi"):
    print(f"  #{c.pk} {c.name!r} supplier={c.is_supplier} manuf={c.is_manufacturer}")
print("== companies matching TE / Tyco / OEG / Vishay / Dale")
for c in Company.objects.filter(Q(name__icontains="TE Conn") | Q(name__icontains="tyco") | Q(name__icontains="OEG") | Q(name__icontains="vishay") | Q(name__icontains="dale")):
    print(f"  #{c.pk} {c.name!r} supplier={c.is_supplier} manuf={c.is_manufacturer}")

def parts(label, q):
    qs = Part.objects.filter(q).distinct()
    print(f"== {label}: {qs.count()}")
    for p in qs:
        print(f"  #{p.pk} active={p.active} stock={p.total_stock} cat={p.category.pathstring if p.category else None} IPN={p.IPN} | {p.name} | {p.description[:90]}")

for t in ["ORWH", "124D1F", "PB2031"]:
    parts(f"part text {t}", Q(name__icontains=t) | Q(description__icontains=t) | Q(IPN__icontains=t) | Q(keywords__icontains=t) | Q(notes__icontains=t))
for t in ["MFP-25", "MFP25", "BRD52", "13-MFP"]:
    parts(f"part text {t}", Q(name__icontains=t) | Q(description__icontains=t) | Q(IPN__icontains=t) | Q(keywords__icontains=t))
parts("relay 24V parts", Q(name__icontains="relay") & (Q(name__icontains="24") | Q(description__icontains="24")))
parts("47k resistors", (Q(name__icontains="47k") | Q(name__icontains="47 k")) & Q(name__icontains="resist"))

print("== supplier parts / manufacturer parts matching")
for sp in SupplierPart.objects.filter(Q(SKU__icontains="PB2031") | Q(SKU__icontains="MFP-25") | Q(SKU__icontains="ORWH")):
    print(f"  sp #{sp.pk} {sp.supplier} {sp.SKU} part#{sp.part_id}")
for mp in ManufacturerPart.objects.filter(Q(MPN__icontains="ORWH") | Q(MPN__icontains="MFP-25")):
    print(f"  mp #{mp.pk} {mp.manufacturer} {mp.MPN} part#{mp.part_id}")

print("== categories holding relays / axial resistors (counts)")
from collections import Counter
for label, q in [("relay", Q(name__icontains="relay")), ("resistor", Q(name__icontains="resistor"))]:
    cnt = Counter(p.category.pathstring if p.category else None for p in Part.objects.filter(q, active=True))
    for k, v in cnt.most_common(12):
        print(f"  {label}: {v:3d}  {k}")
for c in PartCategory.objects.filter(Q(name__icontains="relay") | Q(name__icontains="resist")):
    print(f"  cat #{c.pk} {c.pathstring} parts={c.parts.count()}")

print("== last 5 DigiKey supplier parts (convention)")
for sp in SupplierPart.objects.filter(supplier__name__icontains="digi").order_by("-pk")[:5]:
    print(f"  sp #{sp.pk} SKU={sp.SKU} link={sp.link} pack={sp.pack_quantity} part#{sp.part_id} {sp.part.name} IPN={sp.part.IPN} mp={sp.manufacturer_part}")
print("== last 3 DigiKey POs")
for po in PurchaseOrder.objects.filter(supplier__name__icontains="digi").order_by("-pk")[:3]:
    print(f"  {po.reference} sref={po.supplier_reference} status={po.get_status_display()} desc={po.description}")
    for li in po.lines.all():
        print(f"    {li.part.SKU} qty={li.quantity} @ {li.purchase_price}")
