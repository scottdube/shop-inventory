import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from part.models import Part
from stock.models import StockItem, StockLocation

TERMS = ['antenna','aerial','whip','magnetic mount','mag mount','rf ','coax','coaxial',
         'sma','rp-sma','rpsma','u.fl','ufl','ipex','mcx','mmcx','bnc','tnc','n-type',
         'pigtail','rg174','rg316','rg58','balun','sdr','rtl2832','ads-b','adsb',
         'lora','433mhz','915mhz','868mhz','dipole','ground plane','duplexer','attenuator']

hits = {}
for t in TERMS:
    for p in Part.objects.filter(name__icontains=t):
        hits.setdefault(p.pk, set()).add(f'n~{t.strip()}')
    for p in Part.objects.filter(description__icontains=t):
        hits.setdefault(p.pk, set()).add(f'd~{t.strip()}')

stocked, nostock = [], []
for pk in sorted(hits):
    p = Part.objects.get(pk=pk)
    rows = list(StockItem.objects.filter(part=p))
    (stocked if rows else nostock).append((p, rows, sorted(hits[pk])))

print(f"TERMS SEARCHED ({len(TERMS)}): {', '.join(t.strip() for t in TERMS)}")
print(f"candidates={len(hits)}  WITH STOCK={len(stocked)}  zero-stock stubs={len(nostock)}")
print("="*72)
print("### RF / ANTENNA PARTS THAT PHYSICALLY EXIST")
for p, rows, t in stocked:
    print(f"[{p.pk}] act={p.active} {p.name}")
    print(f"      hit={t}")
    print(f"      defloc={p.default_location}")
    for s in rows:
        print(f"      stock {s.pk} qty={s.quantity} @ {s.location.pathstring if s.location else 'NO LOCATION'}")
print("="*72)
print("### zero-stock (import stubs / never catalogued physically)")
for p, rows, t in nostock:
    print(f"[{p.pk}] {p.name[:90]}")
print("="*72)
print(f"END - {len(stocked)} stocked + {len(nostock)} stubs printed in full, nothing truncated")

print("\n### A0 and B0 contents ###")
for pk in (536, 561):
    cab = StockLocation.objects.get(pk=pk)
    print(f"\n[{cab.pk}] {cab.pathstring}  desc={cab.description!r}")
    for b in StockLocation.objects.filter(parent=cab).order_by('name'):
        rows = StockItem.objects.filter(location=b)
        if rows:
            print(f"   {b.name} [{b.pk}]:")
            for s in rows:
                print(f"       stock {s.pk} [{s.part.pk}] {s.part.name[:62]} qty={s.quantity}")
        else:
            print(f"   {b.name} [{b.pk}]: (no rows)")
