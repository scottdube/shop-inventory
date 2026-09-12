#!/usr/bin/env python3
"""Allocate one power cord splitter to BO-0006 (Cessna Flight Simulator).

PO-0162 brought two; Scott: "1 going to stock 1 to the sim", and then, when
asked where the sim is: *"sim its a build not a location."* So this is an
allocation against a build order, not a stock move.

#1180 was in no BOM, so the allocation needs a BOM line first. That is a real
structural claim -- it says a Cessna Flight Simulator CONTAINS a mains
splitter -- and it was confirmed with Scott ("yes 6 is good") against the two
other sim-named builds (BO-0015 Rudder Pedals, BO-0017 G1000) before writing.
Neither of those takes mains power; this one powers the rig.

The other splitter stays in B0-R1C4 as stock. One row, two units, one of them
allocated -- not two rows, because allocation is what records the commitment
and splitting the row would misstate where the pieces physically are.

    itq run scripts/sim_power_alloc.py
    itq run scripts/sim_power_alloc.py --commit
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from build.models import Build, BuildItem, BuildLine  # noqa: E402
from part.models import BomItem, Part  # noqa: E402
from stock.models import StockItem  # noqa: E402

COMMIT = "--commit" in sys.argv

b = Build.objects.get(reference="BO-0006")
splitter = Part.objects.get(pk=1180)
NOTE = ("Mains input splitter for the sim rig -- one wall outlet feeding two "
        "loads. Added to the BOM 2026-09-12 on receipt of PO-0162, which "
        "brought two: this one and a shelf spare in B0-R1C4.")

print(f"{b.reference}  {b.title}   assembly #{b.part.pk} {b.part.name}")
print(f"allocating: #{splitter.pk} {splitter.name}\n")

bi = BomItem.objects.filter(part=b.part, sub_part=splitter).first()
print(f"  BOM line   : {'exists' if bi else 'MISSING — will create qty 1'}")

rows = list(StockItem.objects.filter(part=splitter).order_by("pk"))
for si in rows:
    print(f"  stock {si.pk}  qty={float(si.quantity):g}  "
          f"free={float(si.unallocated_quantity()):g}  @ {si.location.pathstring}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

if not bi:
    bi = BomItem.objects.create(part=b.part, sub_part=splitter,
                                quantity=1, note=NOTE)
    print(f"\n  + BOM line {bi.pk} created")

line = BuildLine.objects.filter(build=b, bom_item=bi).first()
if not line:
    line = BuildLine.objects.create(build=b, bom_item=bi,
                                    quantity=bi.quantity * b.quantity)
    print(f"  + BuildLine {line.pk} created (qty {float(line.quantity):g})")

need = float(line.quantity) - float(line.allocated_quantity())
if need <= 0:
    print("  ! already fully allocated")
else:
    for si in rows:
        if need <= 0:
            break
        free = float(si.unallocated_quantity())
        if free <= 0:
            continue
        take = min(free, need)
        item, made = BuildItem.objects.get_or_create(
            build_line=line, stock_item=si, defaults={"quantity": take})
        print(f"  + allocated {take:g} from stock {si.pk} ({si.location.name})")
        need -= take
    if need > 0:
        print(f"  << SHORT {need:g}")

line.refresh_from_db()
for si in rows:
    si.refresh_from_db()
    print(f"\n  stock {si.pk}: qty={float(si.quantity):g}  "
          f"allocated={float(si.quantity) - float(si.unallocated_quantity()):g}  "
          f"free={float(si.unallocated_quantity()):g}")
print(f"  build line allocated {float(line.allocated_quantity()):g} "
      f"of {float(line.quantity):g}")
