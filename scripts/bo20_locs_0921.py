import os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockItem, StockLocation
from build.models import Build, BuildItem

for b in Build.objects.filter(reference__in=["BO-0016","BO-0017","BO-0020"]).order_by("reference"):
    print("==", b.reference, b.title, "status", b.status, "qty", b.quantity)
    for bi in BuildItem.objects.filter(build_line__build=b).select_related("stock_item"):
        si = bi.stock_item
        print("   alloc %5.1f  row %-5s %-45s @ %s" % (
            bi.quantity, si.pk, si.part.name[:45], si.location))
print()
print("== Florida Staging rows ==")
for loc in StockLocation.objects.filter(name__icontains="Florida Staging"):
    print("LOC", loc.pk, loc.pathstring)
    for r in StockItem.objects.filter(location=loc).order_by("pk"):
        allocs = BuildItem.objects.filter(stock_item=r)
        tag = ",".join(a.build_line.build.reference for a in allocs) or "-"
        print("   row %-5s %-45s qty %-8s BO:%s" % (r.pk, r.part.name[:45], r.quantity, tag))
