"""Kit check: an assembly's BOM x N boards vs what sits in a kit bin. Read-only.

Written 2026-10-05: Scott wants the AC Wall Adapter for IoT build carried to
Florida as a complete kit - "so I take whatever I need to build them". RB-14 is
known to hold only five BOM rows (TRAPS: "5 rows, 5 counted" is about rows, not
the bin), so the question is which BOM lines are NOT in the kit, and where the
shop's stock of each is.

    itq run scripts/kit_check.py <assembly_pk> <boards> <kit_location_name>
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, BomItem  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

asm = Part.objects.get(pk=int(sys.argv[1]))
n = float(sys.argv[2])
kit = StockLocation.objects.get(name=sys.argv[3])
print(f"{asm.name}  x{n:g} boards  kit={kit.pathstring}\n")
print(f"{'need':>5} {'inkit':>5} {'short':>5}  {'part':60s} elsewhere")
for b in BomItem.objects.filter(part=asm).select_related("sub_part").order_by("reference"):
    p = b.sub_part
    need = float(b.quantity) * n
    rows = StockItem.objects.filter(part=p)
    inkit = sum(float(r.quantity) for r in rows if r.location_id == kit.pk)
    other = [(r.location.name if r.location else "?", float(r.quantity)) for r in rows
             if r.location_id != kit.pk and r.quantity > 0]
    short = max(0.0, need - inkit)
    ref = f"[{b.reference}] " if b.reference else ""
    print(f"{need:5g} {inkit:5g} {short:5g}  {(ref + p.name)[:60]:60s} "
          f"{', '.join(f'{q:g}@{l}' for l, q in other) or '-'}"
          + (f"   NOTE: {b.note[:60]}" if b.note else ""))
