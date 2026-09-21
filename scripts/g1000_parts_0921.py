import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, BomItem
from stock.models import StockItem
for pk in (1137, 1255):
    p = Part.objects.get(pk=pk)
    print("#%s %-22s assembly=%s  BOM lines=%s  stock rows=%s  created %s" % (
        p.pk, p.name, p.assembly, BomItem.objects.filter(part=p).count(),
        StockItem.objects.filter(part=p).count(), p.creation_date))
    print("   desc: %s" % (p.description or "")[:180])
