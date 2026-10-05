"""Read-only: any 47k resistor on hand, and any 0.1% / precision resistor at all?
Searches the requirement (47k, precision) across names, descriptions, keywords,
parameters and kit locations; prints every hit, no cap."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.models import Q
from part.models import Part
from common.models import Parameter
from django.contrib.contenttypes.models import ContentType
from stock.models import StockLocation

def show(label, qs):
    print(f"== {label}: {qs.count()}")
    for p in qs:
        print(f"  pk={p.pk} active={p.active} stock={p.total_stock} cat={p.category} | {p.name} | {p.description[:80]}")

terms47 = ["47k", "47 k", "47K", "47000", "473", "47kohm", "47 kohm"]
q = Q()
for t in terms47:
    q |= Q(name__icontains=t) | Q(description__icontains=t) | Q(keywords__icontains=t)
show("parts matching 47k", Part.objects.filter(q).filter(Q(name__icontains="res") | Q(description__icontains="res")
                                                         | Q(category__name__icontains="res")).distinct())
qp = Q()
for t in ["0.1%", ".1%", "0.05%", "precision", "tolerance 0.1", "B tol", "0.1 %"]:
    qp |= Q(name__icontains=t) | Q(description__icontains=t) | Q(keywords__icontains=t)
show("parts matching 0.1% / precision", Part.objects.filter(qp).distinct())

print("== parameters: tolerance <= 0.1 or resistance 47k")
ct = ContentType.objects.get_for_model(Part)
for pp in Parameter.objects.filter(model_type=ct).filter(Q(template__name__icontains="toler") | Q(template__name__icontains="resist")).select_related("template"):
    d = (pp.data or "").replace(" ", "").lower()
    if any(x in d for x in ["0.1%", "0.05%", "0.01%", "47k", "47000"]):
        part = Part.objects.get(pk=pp.model_id)
        print(f"  part={part.pk} {part.name} | {pp.template.name}={pp.data} stock={part.total_stock}")

print("== resistor kit locations / assortments")
for loc in StockLocation.objects.filter(Q(name__icontains="resist") | Q(description__icontains="resist")
                                        | Q(name__icontains="47k") | Q(description__icontains="47k")):
    print(f"  loc={loc.pk} {loc.pathstring} | {loc.description[:100]}")
show("resistor kits/assortments", Part.objects.filter(Q(name__icontains="resistor") &
        (Q(name__icontains="kit") | Q(name__icontains="assort") | Q(name__icontains="values"))).distinct())
