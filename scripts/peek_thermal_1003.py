"""Read-only: re-read the 2026-10-03 metrology rows in a fresh process (silent-save check)."""
import os, sys, django
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings"); django.setup()
from part.models import Part
from stock.models import StockItem
for pp, sp in ((1317, 896), (1326, 897)):
    p = Part.objects.get(pk=pp); print(p.pk, p.name, "|", p.category.pathstring, "| home:", p.default_location.pathstring)
    s = StockItem.objects.get(pk=sp); print("  SI", s.pk, s.part_id, s.quantity, s.location.pathstring, "SN", s.serial, "| meta:", s.metadata)
