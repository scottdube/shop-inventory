"""Read-only: which LRD label name's barcode hash already exists, and on what.

make_lrd_akro_1025.py --commit stopped on 'Existing barcode found'. InvenTree
hashes barcode_data and refuses a hash any other object already holds.
"""
import os, re, sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from InvenTree.helpers import hash_barcode  # noqa: E402
from stock.models import StockLocation, StockItem  # noqa: E402
from part.models import Part  # noqa: E402
from company.models import SupplierPart, ManufacturerPart  # noqa: E402

PRINTED = re.compile(r"^(Cab[1-8](-[DS][1-5])?|F[0-2](-R\d+C\d+)?)$")
lrd = StockLocation.objects.get(name="LRD", parent=None)
targets = [l for l in lrd.get_descendants() if PRINTED.match(l.name)]
linked = sum(1 for l in targets if l.barcode_data == l.name)
print(f"targets {len(targets)}, already linked {linked}")

from django.apps import apps  # noqa: E402
models = [M for M in apps.get_models() if any(f.name == "barcode_hash" for f in M._meta.fields)]
print("models with barcode_hash:", ", ".join(M.__name__ for M in models))
first = next((l for l in targets if l.barcode_data != l.name), None)
print("first unlinked:", first and first.name)
for l in targets:
    if l.barcode_data == l.name:
        continue
    h = hash_barcode(l.name)
    for M in models:
        if not hasattr(M, "barcode_hash"):
            continue
        for o in M.objects.filter(barcode_hash=h).exclude(pk=l.pk if M is StockLocation else -1):
            print(f"  {l.name}: hash held by {M.__name__} pk {o.pk} "
                  f"({getattr(o, 'pathstring', None) or o}) data={o.barcode_data!r}")
