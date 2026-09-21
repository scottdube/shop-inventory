import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
for p in Part.objects.filter(name__icontains="gma"):
    print("#%-5s %-55s active=%s" % (p.pk, p.name[:55], p.active))
print("---- mosfet / lcd / 10k candidates ----")
for term in ("RFP30N06", "MOSFET", "VS104T", "10.4", "Resistor 10k"):
    hits = Part.objects.filter(name__icontains=term)[:5]
    print("%-14s -> %s" % (term, [(h.pk, h.name[:40]) for h in hits] or "NONE"))
