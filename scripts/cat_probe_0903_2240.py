"""What actually lives in the two competing IC trees, so the sweep files PCF8574AP
where its neighbours already are rather than inventing a third convention."""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402

for pk in (9, 11, 12, 10, 113, 135, 26):
    c = PartCategory.objects.get(pk=pk)
    print("=" * 72)
    print(f"{c.pk}  {c.pathstring}")
    for p in Part.objects.filter(category=c).order_by("pk"):
        print(f"   #{p.pk:<5d} {p.name[:70]}   created={p.creation_date}")
