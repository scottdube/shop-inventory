"""Shorten #1254's name so the 62mm label stops cutting it.

Rendered as created, template 12 gave:
    "Lacing Tape, waxed flat polyester 0.8mm black, 26..."
which loses the spool size and ends mid-number. 'waxed flat polyester' is
three words of material detail that belong in the description, not on a
label read at arm's length in a drawer.

New name is 41 chars and keeps the two facts that identify it in the bin:
the 0.8mm width and the 260m spool.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from part.models import Part

NEW = 'Lacing Tape 0.8mm waxed black, 260m spool'
p = Part.objects.get(pk=1254)
print(f"before ({len(p.name)}): {p.name!r}")
p.name = NEW
p.save()
p2 = Part.objects.get(pk=1254)
print(f"after  ({len(p2.name)}): {p2.name!r}")
print("VERIFIED" if p2.name == NEW else "*** VERIFY FAILED ***")
