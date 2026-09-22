"""Add 4 ft of 24 AWG 3-conductor cable to the Geo Aux Heat BOM (BO-0007).

Second wire line, alongside the 20 AWG 2-core added 2026-09-18 (bo7_add_wire_0918.py).
Reuses existing part 1092 -- searched by gauge + core count first, no duplicate made.

The BOM is an as-built record of a project already in service, so the wire
belongs on it the same way the components do. Adding it as a BOM line on the
assembly part -- not as a one-off note on the build -- is what makes it appear
as an allocatable BuildLine and what keeps the record true if the build is ever
re-run.

Run with --commit to write; bare is a dry run.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, BomItem
from build.models import Build, BuildLine

COMMIT = "--commit" in sys.argv

ASSEMBLY = 834      # Geo Aux Heat
WIRE     = 1092     # Multi-Conductor Cable 24 AWG 3-core, black UL2464  (units: ft)
QTY      = 4
NOTE     = ("4 ft of 24 AWG 3-conductor. Length given by Scott 2026-09-22. "
            "External wiring, not a schematic net on sln-geo-aux-heat.kicad_sch.")

asm  = Part.objects.get(pk=ASSEMBLY)
wire = Part.objects.get(pk=WIRE)
b    = Build.objects.get(reference="BO-0007")
print(f"assembly : {asm.name!r} (pk {asm.pk})")
print(f"sub-part : {wire.name!r} (pk {wire.pk}) units={wire.units!r} stock={wire.total_stock}")
print(f"build    : {b.reference} status={b.status_text} build qty={b.quantity}")

dupe = BomItem.objects.filter(part=asm, sub_part=wire).first()
if dupe:
    print(f"ALREADY PRESENT: BomItem pk={dupe.pk} qty={dupe.quantity} - nothing to do")
    sys.exit(0)

print(f"\nWOULD ADD: BOM line {QTY} ft of part {wire.pk} to {asm.name!r}")
if not COMMIT:
    print("\ndry run - rerun with --commit"); sys.exit(0)

bi = BomItem.objects.create(part=asm, sub_part=wire, quantity=QTY, note=NOTE)
print(f"created BomItem pk={bi.pk}")

# .save() on this install has reported success and written nothing -- re-read.
bi = BomItem.objects.get(pk=bi.pk)
assert bi.quantity == QTY and bi.sub_part_id == WIRE, f"readback wrong: {bi.quantity} {bi.sub_part_id}"
print(f"readback : qty={bi.quantity} sub={bi.sub_part.name!r} note={bi.note[:40]!r}...")

# A new BOM line does not necessarily reach an ALREADY-OPEN build order.
bl = BuildLine.objects.filter(build=b, bom_item=bi).first()
if bl is None:
    bl = BuildLine.objects.create(build=b, bom_item=bi, quantity=QTY * float(b.quantity))
    print(f"BuildLine was missing - created pk={bl.pk}")
bl = BuildLine.objects.get(pk=bl.pk)
print(f"BuildLine: pk={bl.pk} qty={bl.quantity} part={bl.bom_item.sub_part.name!r}")

print("\n=== BO-0007 BOM after ===")
for x in BomItem.objects.filter(part=asm).order_by('pk'):
    print(f"  {x.quantity:>8g} {(x.sub_part.units or 'ea'):<3s} {x.sub_part.name}")
print(f"\nlines: BOM={BomItem.objects.filter(part=asm).count()} "
      f"BuildLine={BuildLine.objects.filter(build=b).count()}")
