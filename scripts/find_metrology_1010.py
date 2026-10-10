"""Read-only: match Scott's metrology-bench photo (2026-10-10) against inventory
before anything is created. Combination square set (iGaging), Starrett Last
Word DTI set, test bar in a wooden case, a drilled steel block."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.models import Q
from part.models import Part
from stock.models import StockItem, StockLocation

GROUPS = {
    "combination square": ["igaging", "combination square", "combo square", "protractor head",
                           "center head", "centre head", "square set"],
    "last word": ["last word", "711", "test indicator"],
    "test bar": ["test bar", "mandrel", "arbor", "alignment bar", "ground bar", "cylindrical square",
                 "master bar", "gauge pin", "gage pin"],
    "block": ["1-2-3", "123 block", "2-4-6", "246 block", "1-2-4", "setup block", "riser block",
              "parallel", "v-block", "v block", "angle block", "gauge block", "gage block"],
}
for g, terms in GROUPS.items():
    q = Q()
    for t in terms:
        q |= Q(name__icontains=t) | Q(keywords__icontains=t) | Q(description__icontains=t)
    hits = Part.objects.filter(q).select_related("category").order_by("pk")
    print(f"\n== {g}: {hits.count()} part(s) -- nothing truncated")
    for p in hits:
        print(f"  part #{p.pk} active={p.active} {p.name[:80]}  [{p.category.pathstring if p.category else '-'}]")
        for s in StockItem.objects.filter(part=p).select_related("location"):
            print(f"      SI #{s.pk} qty={float(s.quantity):g} @ {s.location.pathstring if s.location else 'NO LOCATION'}")
mb = StockLocation.objects.get(pk=381)
print(f"\n{mb.pathstring}: {mb.description!r}; children {[c.name for c in mb.get_children()]}")
for s in StockItem.objects.filter(location__in=mb.get_descendants(include_self=True)).select_related("part"):
    print(f"  SI #{s.pk} {float(s.quantity):g} x {s.part.name[:70]}")
