import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.models import Q
from part.models import Part
from stock.models import StockItem

for val, volts in (("1uF", "50V"), ("10uF", "25V"), ("100uF", "25V")):
    print(f"=== {val} {volts} ===")
    ps = Part.objects.filter(
        Q(name__icontains="electrolytic") & Q(name__icontains=val) & Q(name__icontains=volts)
    ).distinct()
    for p in ps:
        qty = sum(si.quantity for si in StockItem.objects.filter(part=p))
        home = p.default_location.pathstring if p.default_location else "-- no home --"
        print(f"   #{p.pk:<4} {p.name:<42} stock={qty:g}")
        print(f"         home: {home}")
    if not ps:
        print("   none")
    print()

print("total electrolytic parts:",
      Part.objects.filter(name__icontains="Capacitor Electrolytic").count())
print("of those with any stock:",
      sum(1 for p in Part.objects.filter(name__icontains="Capacitor Electrolytic")
          if StockItem.objects.filter(part=p).exists()))
