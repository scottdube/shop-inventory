import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem
from build.models import Build

print("=== 10.4in displays ===")
for p in Part.objects.filter(name__icontains="10.4") | Part.objects.filter(name__icontains="VSDISPLAY"):
    for r in StockItem.objects.filter(part=p):
        print("  #%-5s %-46s row %-5s qty %-6s @ %s" % (
            p.pk, p.name[:46], r.pk, r.quantity, r.location))
    if not StockItem.objects.filter(part=p).exists():
        print("  #%-5s %-46s NO STOCK ROW" % (p.pk, p.name[:46]))

print("\n=== older / superseded G1000 boards ===")
for p in Part.objects.filter(name__icontains="G1000"):
    oh = sum(float(r.quantity) for r in StockItem.objects.filter(part=p))
    print("  #%-5s %-52s active=%-5s on hand %s" % (p.pk, p.name[:52], p.active, oh))

print("\n=== all builds ===")
for b in Build.objects.all().order_by("reference"):
    print("  %-9s %-44s status %s" % (b.reference, b.title[:44], b.status))
