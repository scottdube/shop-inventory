"""Read-only: list every location under LRD/Bench Wall with its barcode_data."""
import os, sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockLocation  # noqa: E402

bench = StockLocation.objects.get(name="Bench Wall", parent__name="LRD", parent__parent=None)
for l in bench.get_descendants(include_self=False).order_by("tree_id", "lft"):
    print(f"{'  ' * (l.level - bench.level)}{l.name}  [pk {l.pk}] barcode={l.barcode_data!r}")
