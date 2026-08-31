"""Which category tree is current practice? Read-only.

The dupe probe surfaced two parallel homes for the same concepts — flat legacy
("Switches" #33, seeded from purchase history) and nested ("Electronics/
Electromechanical/Switches" #111). Guessing between them would scatter these
four parts. Ask the data instead: what have the most recently created parts
actually used?
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

print("30 most recently created parts — pk, category, name:")
for p in Part.objects.order_by("-pk")[:30]:
    print(f"  #{p.pk:5d}  [{p.category.pathstring if p.category else 'NONE'}]  {p.name[:58]}")
