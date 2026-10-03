"""Read-only: re-read the comparator rows in a fresh process (silent-save check)."""
import os, sys, django
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings"); django.setup()
from part.models import Part
from stock.models import StockItem
p = Part.objects.get(pk=1317); print(p.pk, p.name, "|", p.category.pathstring, "| home:", p.default_location.pathstring)
s = StockItem.objects.get(pk=896); print(s.pk, s.part_id, s.quantity, s.location.pathstring)
