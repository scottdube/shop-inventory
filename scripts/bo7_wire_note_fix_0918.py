"""Correct the provenance on the BO-0007 wire line: Scott MEASURED the 5 ft."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import BomItem

NEW = ("5 ft of 20 AWG 2-conductor. Length MEASURED off the installation by "
       "Scott, 2026-09-18. Not on sln-geo-aux-heat.kicad_sch - this is the "
       "external wiring run, not a schematic net.")

bi = BomItem.objects.get(pk=103)
print(f"before: {bi.note!r}")
bi.note = NEW
bi.save()

bi = BomItem.objects.get(pk=103)          # .save() has written nothing before
if bi.note != NEW:
    print("save() did not stick - falling back to queryset update()")
    BomItem.objects.filter(pk=103).update(note=NEW)
    bi = BomItem.objects.get(pk=103)
assert bi.note == NEW, "note did not write"
print(f"after : {bi.note!r}")
print(f"qty={bi.quantity} sub={bi.sub_part.name!r}  OK")
