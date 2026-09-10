import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from company.models import Company
from stock.models import StockLocation, StockItem
from part.models import Part
print("=== JLCPCB supplier? ===")
for c in Company.objects.filter(name__icontains="jlc"):
    print(f"   #{c.pk} {c.name}  supplier={c.is_supplier}")
else:
    if not Company.objects.filter(name__icontains="jlc").exists(): print("   none — needs creating")
print("\n=== staging / LRD-bound locations ===")
for l in StockLocation.objects.filter(name__iregex=r'stag|florida|LRD|ship|outbound|box')[:12]:
    print(f"   #{l.pk} {l.pathstring}")
print("\n=== what carries a florida earmark today ===")
n=0
for s in StockItem.objects.all():
    if (s.metadata or {}).get("florida"):
        print(f"   {s.part.name[:40]:40} qty={s.quantity:g} @ {s.location.name if s.location else '-'}"); n+=1
print(f"   ({n} earmarked)")
print("\n=== the ad-hoc PCB stock row I created ===")
p = Part.objects.get(name="HoT Info Orbs PCB v1.1")
for s in StockItem.objects.filter(part=p):
    print(f"   stock {s.pk}: qty={s.quantity:g} @ {s.location.pathstring if s.location else '-'} PO={s.purchase_order or '-'} price={s.purchase_price}")
