"""What BO-0016 currently claims, against what was actually built."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from build.models import Build, BuildLine, BuildItem
from stock.models import StockItem

b = Build.objects.get(reference="BO-0016")
print(f"{b.reference}  '{b.title}'  qty={b.quantity:g}  status={b.status}")
print(f"   /web/manufacturing/build-order/{b.pk}")
print("\ncurrent BOM lines:")
for line in BuildLine.objects.filter(build=b):
    sub = line.bom_item.sub_part
    alloc = sum(bi.quantity for bi in BuildItem.objects.filter(build_line=line))
    free = sum(s.unallocated_quantity() for s in StockItem.objects.filter(part=sub))
    print(f"   {line.bom_item.quantity:g}x  #{sub.pk:4} {sub.name[:46]:46} allocated={alloc:g} free_stock={free:g}")
