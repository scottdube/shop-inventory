"""What does this instance already use to distinguish a TOOL from shelf stock?

Question is whether an 'asset type' exists. InvenTree has no asset model, so
the answer has to be reconstructed from what is actually in use: the category
tree, the boolean flags, and whether equipment is serialised.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory
from stock.models import StockItem

print("=== categories with 'equip'/'tool'/'machine'/'asset' in the path ===")
for c in PartCategory.objects.all():
    p = c.pathstring.lower()
    if any(k in p for k in ("equip", "tool", "machine", "asset", "instrument")):
        print(f"  {c.pk:4d} {c.pathstring:55s} parts={c.parts.count()}")

print("\n=== flag usage across the whole catalogue ===")
tot = Part.objects.count()
for f in ("trackable", "purchaseable", "salable", "assembly", "component", "virtual", "is_template"):
    print(f"  {f:14s} True={Part.objects.filter(**{f: True}).count():5d}  of {tot}")

print("\n=== the QL-810W part(s) ===")
for p in Part.objects.filter(name__icontains="QL-810"):
    print(f"  #{p.pk} {p.name!r}")
    print(f"      category={p.category.pathstring if p.category else None}")
    print(f"      trackable={p.trackable} purchaseable={p.purchaseable} component={p.component} "
          f"assembly={p.assembly} active={p.active}")
    print(f"      IPN={p.IPN!r} units={p.units!r} minimum_stock={p.minimum_stock}")
    for si in StockItem.objects.filter(part=p):
        print(f"      STOCK #{si.pk} qty={si.quantity} serial={si.serial!r} "
              f"loc={si.location.pathstring if si.location else None} status={si.status}")

print("\n=== trackable parts that DO exist (the precedent, if any) ===")
for p in Part.objects.filter(trackable=True)[:20]:
    print(f"  #{p.pk} {p.name[:60]:60s} {p.category.pathstring if p.category else ''}")
