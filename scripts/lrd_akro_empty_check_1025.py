"""Read-only: count F0/F1/F2 drawers whose description starts VERIFIED EMPTY."""
import os, sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockLocation, StockItem  # noqa: E402

for cab, want in (("F0", 24), ("F1", 64), ("F2", 64)):
    rows = StockLocation.objects.filter(parent__name=cab, parent__parent__name="Akro Bins")
    ok = sum(1 for l in rows if (l.description or "").startswith("VERIFIED EMPTY"))
    items = StockItem.objects.filter(location__in=rows).count()
    print(f"{cab}: {ok}/{rows.count()} verified empty (expected {want}), stock rows {items}")
print("sample:", rows.first().description)
