"""READ-ONLY: what fields does StockLocation actually have, and where do
existing locations keep their long-form explanation?"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockLocation  # noqa: E402

print("concrete fields on StockLocation:")
for f in StockLocation._meta.get_fields():
    if getattr(f, "concrete", False):
        print(f"  {f.name:<24} {type(f).__name__:<22} "
              f"max_length={getattr(f, 'max_length', None)}")

print()
print("does it have a notes attribute at all?")
print(f"  hasattr(StockLocation, 'notes') = {hasattr(StockLocation, 'notes')}")

print()
print("a location with a long description -- how long do these run?")
for loc in StockLocation.objects.exclude(description="").order_by("-pk")[:5]:
    print(f"  #{loc.pk} {loc.pathstring}")
    print(f"      desc ({len(loc.description)} chars): {loc.description[:150]}")
