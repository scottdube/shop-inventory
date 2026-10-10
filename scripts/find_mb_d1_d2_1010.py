"""Read-only: match Scott's photos of Metrology Bench drawers D1 and D2
(2026-10-10) against inventory before anything is moved or created."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.models import Q
from part.models import Part
from stock.models import StockItem, StockLocation

GROUPS = {
    "CR2032": ["cr2032", "2032"],
    "taytools": ["taytools", "tay tools"],
    "federal": ["federal"],
    "mitutoyo / outside mic": ["mitutoyo", "103-", "outside micrometer"],
    "depth mic": ["depth micrometer", "129-"],
    "starrett indicator": ["25-441", "starrett 25"],
    "telescoping": ["telescop", "telescoping gage", "telescoping gauge", "snap gage"],
    "angle-izer": ["angle-izer", "angleizer", "general tools", "protractor"],
    "pitch / feeler / leaf": ["pitch gage", "pitch gauge", "feeler", "thickness gage", "leaf"],
    "starrett misc": ["starrett"],
    "parallels": ["parallel"],
    "plug gauge": ["plug gage", "plug gauge", "go-no", "go no", "go/no", "thread gage", "thread gauge", "sutool", "2b"],
    "roughness": ["roughness"],
    "caliper": ["caliper", "vinca", "dcla"],
    "hardness": ["hardness", "tsubosan", "hrc"],
    "thread wires": ["thread measuring", "measuring wire", "3-wire", "three wire", "thread wire"],
    "spanner": ["spanner"],
    "surface gage": ["surface gage", "surface gauge", "257"],
}
for g, terms in GROUPS.items():
    q = Q()
    for t in terms:
        q |= Q(name__icontains=t) | Q(keywords__icontains=t) | Q(description__icontains=t)
    hits = Part.objects.filter(q).select_related("category").order_by("pk")
    print(f"\n== {g}: {hits.count()} part(s) -- nothing truncated")
    for p in hits:
        rows = list(StockItem.objects.filter(part=p).select_related("location"))
        print(f"  part #{p.pk} {'' if p.active else 'INACTIVE '}{p.name[:80]}  [{p.category.pathstring if p.category else '-'}]")
        for s in rows:
            print(f"      SI #{s.pk} qty={float(s.quantity):g} @ {s.location.pathstring if s.location else 'NO LOCATION'}")
mb = StockLocation.objects.get(pk=381)
print(f"\n== everything under {mb.pathstring}")
for s in StockItem.objects.filter(location__in=mb.get_descendants(include_self=True)).select_related("part", "location").order_by("location__name"):
    print(f"  {s.location.name:16} SI #{s.pk} {float(s.quantity):g} x {s.part.name[:70]}")
