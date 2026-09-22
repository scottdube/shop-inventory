"""Read-only: find a 24 AWG 3-conductor cable part, plus BO-0007's current state.

Searches the REQUIREMENT (gauge + core count), not a part number, and prints
every match with active/units/stock so nothing is filtered out silently.
"""
import os, sys, re, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.models import Q
from part.models import Part, BomItem
from build.models import Build, BuildLine

q = Q()
for t in ("24 awg", "24awg", "24-awg", "awg 24", "24 ga", "3-core", "3 core", "3-conductor",
          "3 conductor", "3c ", "multi-conductor", "multiconductor", "cable"):
    q |= Q(name__icontains=t) | Q(description__icontains=t)
rows = Part.objects.filter(q).order_by("pk")
print(f"candidates matching any wire/cable term: {rows.count()} (all printed)")
for p in rows:
    text = f"{p.name} {p.description or ''}".lower()
    g24 = bool(re.search(r"24\s*-?\s*(awg|ga)", text))
    c3 = bool(re.search(r"\b3\s*-?\s*(core|conductor|c\b|wire)", text))
    flag = ("<== 24AWG+3C" if g24 and c3 else "   24AWG" if g24 else "   3C" if c3 else "")
    print(f"  pk={p.pk:<5} active={p.active!s:<5} units={p.units or 'ea':<4} "
          f"stock={p.total_stock:<8g} {p.name[:70]!r} {flag}")

b = Build.objects.get(reference="BO-0007")
print(f"\n{b.reference} part={b.part.name!r} (pk {b.part.pk}) status={b.status_text} qty={b.quantity}")
for x in BomItem.objects.filter(part=b.part).order_by("pk"):
    print(f"  BOM pk={x.pk:<4} {x.quantity:>6g} {(x.sub_part.units or 'ea'):<3s} {x.sub_part.name}")
print(f"lines: BOM={BomItem.objects.filter(part=b.part).count()} "
      f"BuildLine={BuildLine.objects.filter(build=b).count()}")
