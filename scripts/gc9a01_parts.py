"""What GC9A01 parts exist, so BO-0016 can point at the right one."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem
from build.models import Build, BuildLine, BuildItem

for p in Part.objects.filter(name__icontains="GC9A01").order_by("pk"):
    qty = sum(s.quantity for s in StockItem.objects.filter(part=p))
    print(f"\n#{p.pk} {p.name}")
    print(f"   desc: {(p.description or '')[:100]}")
    print(f"   stock: {qty:g}")
    if p.notes: print(f"   notes: {p.notes[:150].strip()}")

b = Build.objects.filter(reference="BO-0016").first()
print(f"\n=== {b.reference} BOM lines ===")
for line in BuildLine.objects.filter(build=b):
    sub = line.bom_item.sub_part
    alloc = sum(bi.quantity for bi in BuildItem.objects.filter(build_line=line))
    print(f"   {line.bom_item.quantity:g}x #{sub.pk} {sub.name[:45]:45} allocated={alloc:g}")
