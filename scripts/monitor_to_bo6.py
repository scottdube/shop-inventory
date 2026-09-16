#!/usr/bin/env python3
"""Allocate the VSDISPLAY bar monitor to BO-0006 and record where it really is.

Scott, 2026-09-16: "it is inteneded for the sim build", then BO-0006 (Cessna
Flight Simulator) and "at the sim" when asked which build and where it sits.

ALLOCATED, NOT CONSUMED. "Intended for" is not "fitted to". The M4x40 screws
on this same build were consumed because they are in the machine; this is not
yet. Same build, third different treatment, and each one tracks a different
physical fact.

LOCATION IS THE HONEST PROBLEM HERE. It is physically at the sim rig, and the
rig is not a location in InvenTree -- Scott, 2026-09-12: "sim its a build not
a location." So the row sits at the SLN site root with a note saying exactly
where it actually is. That is vague, and it is vague ON PURPOSE rather than
inventing a location he has told me not to create.

This is the SECOND item to need "at the sim" as a place (the power cord
splitter was the first). If a third appears, the answer stops being a note and
starts being a question worth re-asking -- but it is his shop and he has
already answered it once.

    itq run scripts/monitor_to_bo6.py
    itq run scripts/monitor_to_bo6.py --commit
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
p = Part.objects.get(pk=1188)
rows = list(StockItem.objects.filter(part=p).select_related("location"))
print(f"{b.reference} {b.title}")
print(f"part #{p.pk} {p.name}")
for si in rows:
    print(f"  stock {si.pk} qty={float(si.quantity):g} @ "
          f"{si.location.pathstring if si.location else 'NO LOCATION'}")

bi = BomItem.objects.filter(part=b.part, sub_part=p).first()
print(f"  BOM line: {'exists' if bi else 'MISSING — will create qty 1'}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

if not bi:
    bi = BomItem.objects.create(
        part=b.part, sub_part=p, quantity=1,
        note="Instrument-panel bar display, 1920x515. Added to the BOM "
             "2026-09-16 on receipt of PO-0168.")
    print(f"  + BOM line {bi.pk}")

line = BuildLine.objects.filter(build=b, bom_item=bi).first()
if not line:
    line = BuildLine.objects.create(build=b, bom_item=bi,
                                    quantity=bi.quantity * b.quantity)
    print(f"  + BuildLine {line.pk}")

need = float(line.quantity) - float(line.allocated_quantity())
for si in rows:
    if need <= 0:
        break
    free = float(si.unallocated_quantity())
    if free <= 0:
        continue
    take = min(free, need)
    BuildItem.objects.get_or_create(build_line=line, stock_item=si,
                                    defaults={"quantity": take})
    print(f"  + allocated {take:g} from stock {si.pk}")
    need -= take

for si in rows:
    si.refresh_from_db()
    StockItem.objects.filter(pk=si.pk).update(notes=(si.notes or "").rstrip() + (
        "\n\nPHYSICALLY AT THE SIM RIG. Scott, 2026-09-16: \"at the sim\". The "
        "rig is NOT a location in InvenTree — he was explicit on 2026-09-12 "
        "that \"sim its a build not a location\" — so this row sits at the SLN "
        "site root and this note carries the real whereabouts. Vague on "
        "purpose, rather than inventing a location.\n\n"
        "ALLOCATED to BO-0006, not consumed: intended for the build, not yet "
        "fitted."))

line.refresh_from_db()
print(f"\n  build line allocated {float(line.allocated_quantity()):g} of "
      f"{float(line.quantity):g}")
