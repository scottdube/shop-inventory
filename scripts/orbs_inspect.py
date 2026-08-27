"""Read-only: what does inventory already know that an Info Orbs build would need?"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory
from build.models import Build
from stock.models import StockItem

cat = PartCategory.objects.filter(name="Projects", parent=None).first()
print("=== Projects category ===")
if cat:
    for p in Part.objects.filter(category=cat).order_by("pk"):
        b = Build.objects.filter(part=p).first()
        print(f"  #{p.pk:5} {p.name[:55]:55} build={b.reference if b else '-'}")
else:
    print("  (no Projects category)")

print("\n=== existing builds (reference numbering) ===")
for b in Build.objects.all().order_by("pk"):
    print(f"  {b.reference:12} {b.title[:50]:50} status={b.status}")

TERMS = ["ESP32", "GC9A01", "TFT", "round display", "1.28", "240x240",
         "pushbutton", "push button", "tactile", "momentary"]
print("\n=== candidate parts already in inventory ===")
for t in TERMS:
    hits = Part.objects.filter(name__icontains=t)[:8]
    if not hits:
        continue
    print(f"  -- {t}")
    for p in hits:
        qty = sum(s.quantity for s in StockItem.objects.filter(part=p))
        avail = sum(s.unallocated_quantity() for s in StockItem.objects.filter(part=p))
        loc = ", ".join(sorted({s.location.name for s in StockItem.objects.filter(part=p) if s.location}))
        print(f"     #{p.pk:5} {p.name[:48]:48} qty={qty:g} avail={avail:g} @ {loc[:40]}")
