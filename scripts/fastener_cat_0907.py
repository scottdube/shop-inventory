"""Read-only: where do fasteners actually live, and what else is in End Mills?

pk 1177 "Flat Head Cap Screw M4 x 40mm" is filed under
Tooling/Cutting Tools/End Mills. A screw is not an end mill, so either the part
is misfiled or the category has been used as a dumping ground — and the fix has
to come from PRECEDENT (where the other 90-odd screws live), not from my taste.

Prints three things: the categories every screw/bolt/washer/nut-named part sits
in, the full contents of the End Mills category, and the sibling created the
same day (pk 1178) so a systematic import bug is visible if there is one.
"""
import os
import sys
from collections import Counter

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402

FASTENER = (Q(name__icontains="screw") | Q(name__icontains="bolt")
            | Q(name__icontains="washer") | Q(name__icontains="nut")
            | Q(name__icontains="SHCS") | Q(name__icontains="cap screw"))

print("-- category histogram for fastener-named parts --")
hist = Counter()
for p in Part.objects.filter(FASTENER):
    hist[p.category.pathstring if p.category else "(none)"] += 1
for path, n in hist.most_common():
    print(f"   {n:4d}  {path}")

print()
print("-- full contents of Tooling/Cutting Tools/End Mills --")
cat = PartCategory.objects.filter(pathstring="Tooling/Cutting Tools/End Mills").first()
if not cat:
    print("   (no such category)")
else:
    for p in Part.objects.filter(category=cat).order_by("pk"):
        print(f"   pk {p.pk:5d} | {p.name[:56]:<56} | created {p.creation_date} "
              f"| active={p.active}")

print()
print("-- the two parts created 2026-09-06 alongside 1177 --")
for pk in (1175, 1176, 1177, 1178):
    p = Part.objects.filter(pk=pk).first()
    if p:
        print(f"   pk {pk:5d} | {p.name[:44]:<44} | "
              f"{p.category.pathstring if p.category else '(none)'}")

print()
print("-- candidate destination categories (anything hardware-ish) --")
for c in PartCategory.objects.all().order_by("pathstring"):
    low = c.pathstring.lower()
    if any(k in low for k in ("fasten", "hardware", "screw", "mechanic")):
        print(f"   {c.pk:4d}  {c.pathstring}  ({Part.objects.filter(category=c).count()} parts)")
