#!/usr/bin/env python3
"""PS-011's barrel measured: 3.5 mm OD. Record it, and downgrade the hazard.

Scott, 2026-09-19: "3.5mm". Unqualified figure from Scott = measured.

The 48 V warning on this part assumed the plug might fit the 12 V and 24 V
bricks beside it in B-02. It cannot: every DC barrel recorded in the catalogue
is 5.5 mm. Downgraded rather than deleted, and the residual risk is named
rather than declared absent -- the search was of the CATALOGUE, and 3.5 mm is a
common jack on small consumer gear that has no record here.

    itq run scripts/ps011_barrel.py [--commit]
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

COMMIT = "--commit" in sys.argv
PK = 1225

NEW_DESC = ("Mains adapter for the D-Link DWL-P200 PoE base unit. 100-240VAC in, "
            "48VDC 400mA out. Barrel 3.5mm OD (ID not measured). Only 48V supply "
            "known on site; does not fit the 5.5mm gear beside it.")

OLD = """**48 V IS THE ODD ONE OUT IN THIS SHOP AND THAT IS THE HAZARD.** Bin B-02 is otherwise 12 V and 24 V bricks, and a 48 V supply with a barrel plug that fits them is a way to destroy something quietly. It exists to feed a PoE base unit and nothing else.

**The barrel size and polarity are NOT recorded — measure them before this is filed next to the 12 V and 24 V bricks.** If it physically mates with the 12 V gear in the same bin, that is worth knowing and worth separating."""

NEW = """**BARREL MEASURED 2026-09-19: 3.5 mm OD** (Scott). **Inner diameter NOT measured** — 3.5 mm OD conventionally pairs with a 1.35 mm pin, but that is the convention, not a reading of this plug. Polarity also not recorded.

**That measurement downgrades the hazard, and it is the geometry that does it.** The concern was a 48 V supply sitting in a bin of 12 V and 24 V bricks. It cannot reach them: **every DC barrel recorded in the catalogue is 5.5 mm** — PS-002 and PS-009 are 5.5x2.1, PS-010 is 5.5x2.5. A 3.5 mm plug does not enter a 5.5 mm jack. The 48 V can only go where it is meant to go, into a POE-003 base unit.

**What that claim actually rests on, so it is not over-read:** a search of ACTIVE parts' name, description and keywords for a 3.5 mm barrel, plus a listing of every barrel size recorded under Electronics/Power. Notes fields were not searched, and **the catalogue is not the shop.** 3.5x1.35 is a common jack on small consumer hardware — old routers, hubs, scales, desk gear — none of which is necessarily in here. **A 3.5 mm barrel arriving in the shop later re-opens this**, and so does an uncatalogued device already on a bench.

So: not the live hazard it was written as, but not "cannot happen" either. It exists to feed a PoE base unit and nothing else."""

p = Part.objects.get(pk=PK)
print(f"#{p.pk} {p.name}")
if OLD not in p.notes:
    print("  anchor MISSING — aborting rather than writing a half edit")
    sys.exit(1)
print("  anchor found; hazard paragraph will be replaced with the measurement")
print(f"  description {len(NEW_DESC)}/250")
if len(NEW_DESC) > 250:
    sys.exit("description too long")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

Part.objects.filter(pk=PK).update(notes=p.notes.replace(OLD, NEW, 1), description=NEW_DESC)
p.refresh_from_db()
print("\n  3.5mm recorded:        ", "BARREL MEASURED 2026-09-19: 3.5 mm OD" in p.notes)
print("  ID marked unmeasured:  ", "Inner diameter NOT measured" in p.notes)
print("  search scope named:    ", "the catalogue is not the shop" in p.notes)
print("  old hazard text gone:  ", OLD not in p.notes)
print("  description updated:   ", "3.5mm OD" in p.description)
