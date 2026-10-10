"""Read-only: find the Andonstar microscope, the oscilloscope, a 2-3" micrometer
and dial indicators before the Florida pack adds anything. 2026-10-10."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.models import Q
from part.models import Part
from stock.models import StockItem

GROUPS = {
    "microscope": ["andonstar", "microscope", "ad246", "ad249", "ad407", "ad409"],
    "oscilloscope": ["oscilloscope", "rigol", "dho9", "dho8", "ds1054", "scope"],
    "micrometer": ["micrometer", "mitutoyo", "starrett", "outside mic"],
    "dial indicator": ["dial indicator", "indicator", "test indicator", "dti", "interapid", "last word"],
}
for g, terms in GROUPS.items():
    q = Q()
    for t in terms:
        q |= Q(name__icontains=t) | Q(keywords__icontains=t) | Q(description__icontains=t)
    hits = Part.objects.filter(q).select_related("category").order_by("pk")
    print(f"\n== {g}: {hits.count()} part(s) (terms {terms}) -- nothing truncated")
    for p in hits:
        print(f"  part #{p.pk} active={p.active} {p.name[:70]}  [{p.category.pathstring if p.category else '-'}]"
              f"  default={p.default_location.pathstring if p.default_location else '-'}")
        for s in StockItem.objects.filter(part=p).select_related("location"):
            m = s.metadata or {}
            print(f"      SI #{s.pk} qty={float(s.quantity):g} @ {s.location.pathstring if s.location else 'NO LOCATION'}"
                  f" commutes={bool(m.get('commutes'))} florida={bool(m.get('florida'))}")
