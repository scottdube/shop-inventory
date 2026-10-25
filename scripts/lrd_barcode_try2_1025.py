"""Link two LRD labels one at a time and re-read: Cab5-S1 (bench wall) and F1-R3C6.

The batch link in make_lrd_akro_1025.py stopped on 'Existing barcode found' at
F1-R3C6 with every bench-wall name still unlinked, yet nothing holds either hash.
This writes ONE barcode each through assign_barcode and reads the row back by pk.
"""
import os, sys, traceback
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from InvenTree.helpers import hash_barcode  # noqa: E402
from stock.models import StockLocation  # noqa: E402

for name, parent in (("Cab5-S1", "Cab5"), ("F1-R3C6", "F1")):
    loc = StockLocation.objects.get(name=name, parent__name=parent)
    print(f"{name} pk {loc.pk}: before data={loc.barcode_data!r} hash={loc.barcode_hash!r}")
    print(f"  lookup -> {StockLocation.lookup_barcode(hash_barcode(name))}")
    try:
        loc.assign_barcode(barcode_data=name, raise_error=True)
    except Exception:
        traceback.print_exc()
    back = StockLocation.objects.get(pk=loc.pk)
    print(f"  after re-read data={back.barcode_data!r} hash={back.barcode_hash!r}")
