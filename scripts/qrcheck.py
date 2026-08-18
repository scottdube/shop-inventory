"""Can InvenTree resolve a drawer address QR? One batched check."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockLocation

probes = ["A1-R1C1", "B3-R2C5", "A2-R4C7"]
print("== does the location exist ==")
for p in probes:
    loc = StockLocation.objects.filter(name=p).first()
    print(f"  {p:10} {'FOUND  ' + loc.pathstring if loc else 'MISSING'}")

print("\n== is a barcode linked to it ==")
for p in probes:
    loc = StockLocation.objects.filter(name=p).first()
    if not loc:
        continue
    bd = getattr(loc, "barcode_data", "") or ""
    bh = getattr(loc, "barcode_hash", "") or ""
    print(f"  {p:10} data={bd!r:26} hash={bh[:12]!r}")

total = StockLocation.objects.count()
with_bc = StockLocation.objects.exclude(barcode_data="").count()
print(f"\nlocations: {total}   with a linked barcode: {with_bc}")
print("\nverdict:", "READY — scanning a label finds the drawer" if with_bc
      else "NOT LINKED — a scan returns 'barcode not found' until we link them")
