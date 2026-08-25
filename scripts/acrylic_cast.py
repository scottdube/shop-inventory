"""Record that #1083 is CAST — Scott's call, 2026-08-24, not the listing's.

Part.description is hard-capped at 250 chars on this install AND validated,
unlike StockLocation.description which happily took 334. Check the length
before writing, and re-read after.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part                                    # noqa: E402

NEW = ("Outus clear acrylic (PMMA) sheet, 12 x 12 in, 1/16 in (1.6 mm) thick. "
       "Sold in 4-packs. CAST - confirmed by Scott 2026-08-24, not seller copy. "
       "Cast lasers cleanly; extruded melts and gums the edge. "
       "orig: Outus 4 Pcs 12 x 12 Inch Clear Acrylic Sheet")

print(f"length {len(NEW)} / 250")
assert len(NEW) <= 250, "too long - it would be silently refused or truncated"

p = Part.objects.get(pk=1083)
print(f"was: {p.description}")
Part.objects.filter(pk=1083).update(description=NEW)
got = Part.objects.get(pk=1083).description
assert got == NEW, f"did not stick, got {len(got)} chars: {got[-40:]!r}"
print(f"\nnow: {got}")
