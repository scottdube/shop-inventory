"""Read-only: does the shop already own a surface-finish comparator or roughness tester?
Searches part name/description/keywords for the requirement, not a model number."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.models import Q
from part.models import Part

TERMS = ["rough", "finish compar", "comparator", "microfinish", "profilomet", "surface finish",
         "surface gauge", " ra ", "rubert", "flexbar", "gar ", "specimen"]
q = Q()
for t in TERMS:
    q |= Q(name__icontains=t) | Q(description__icontains=t) | Q(keywords__icontains=t)
rows = Part.objects.filter(q).distinct()
print(f"{rows.count()} parts matched (all printed, no cap)")
for p in rows:
    print(f"pk={p.pk} active={p.active} stock={p.total_stock} | {p.name} | {p.description[:80]}")
