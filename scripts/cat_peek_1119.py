"""List the parts in a few categories, to place a new part beside its nearest siblings."""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402

for pk in [int(a) for a in sys.argv[1:]]:
    c = PartCategory.objects.get(pk=pk)
    print(f"#{pk} {c.pathstring}")
    for p in Part.objects.filter(category=c, active=True):
        print(f"   - {p.name}")
