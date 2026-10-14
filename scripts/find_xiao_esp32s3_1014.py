"""Is a Seeed XIAO ESP32-S3 (or S3 Plus) in stock, and where?

Searches the REQUIREMENT, not a part number: any part whose name, description,
keywords or IPN mentions XIAO / ESP32-S3 / ESP32S3 / Seeed, plus any supplier
part or manufacturer part that does. Prints every match with its stock rows
and their locations, so a near-miss (plain ESP32-S3 module, C3 XIAO) is seen
rather than read as "none".
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()  # itq run does not bootstrap Django

from django.db.models import Q
from part.models import Part
from company.models import SupplierPart, ManufacturerPart
from stock.models import StockItem

terms = ["xiao", "esp32-s3", "esp32s3", "esp32 s3", "seeed"]
q = Q()
for t in terms:
    q |= Q(name__icontains=t) | Q(description__icontains=t) | Q(keywords__icontains=t) | Q(IPN__icontains=t)
parts = set(Part.objects.filter(q))
for sp in SupplierPart.objects.filter(Q(SKU__icontains="xiao") | Q(SKU__icontains="102010671") | Q(SKU__icontains="113991114") | Q(description__icontains="xiao")):
    parts.add(sp.part)
for mp in ManufacturerPart.objects.filter(Q(MPN__icontains="xiao") | Q(description__icontains="xiao")):
    parts.add(mp.part)

print(f"terms={terms}  matching parts: {len(parts)}  (all rows shown, nothing cut)")
for p in sorted(parts, key=lambda p: p.name.lower()):
    items = StockItem.objects.filter(part=p)
    total = sum(i.quantity for i in items)
    print(f"\n[{p.pk}] {p.name}  active={p.active}  total_stock={total}  /web/part/{p.pk}/")
    if p.description:
        print(f"      {p.description[:110]}")
    for i in items:
        loc = i.location.pathstring if i.location else "(no location)"
        print(f"      stock {i.pk}: qty {i.quantity}  @ {loc}  /web/stock/item/{i.pk}/")
