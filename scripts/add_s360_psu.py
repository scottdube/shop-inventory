#!/usr/bin/env python3
"""Catalogue the S-360-12 enclosed switching PSU.

Wire-shelf stock-in, 2026-09-14. Read off the case label:

    S-360-12    AC INPUT 110/220V +/-15%    DC OUTPUT 12V 30A    CE, SGS PASS

Sibling of #1160 S-250-24, same S-series enclosed format, so it is catalogued
the same way: Electronics/Power, specs in the description, traps in the notes.

THE 110/220 INPUT IS THE DANGEROUS PART AND THE LABEL WON'T TELL YOU. S-series
supplies take both mains voltages via a SMALL SLIDE SWITCH on the case, not by
auto-ranging. Set to 110 and plugged into 220, it fails instantly and
destructively. Set to 220 on a 110 V outlet it simply will not start, which is
the harmless direction and the one that gets diagnosed as "dead supply".
CHECK THE SWITCH BEFORE FIRST POWER-UP, every time, on any supply of this
family. Whether THIS unit has the switch has NOT been verified -- it is a
property of the family, so it is written as what to check, not as a fact about
this unit.

No count and no location are set here. Both come from Scott.

    itq run scripts/add_s360_psu.py
    itq run scripts/add_s360_psu.py --commit
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402

COMMIT = "--commit" in sys.argv

NAME = "S-360-12 Switching Power Supply, 12V 30A 360W, enclosed"
DESC = ("Enclosed switch-mode PSU. AC 110/220V +/-15% in, DC 12V 30A 360W out. "
        "Perforated steel case, screw-terminal output, no mains cord supplied. "
        "Read from the case label 2026-09-14.")
KEYWORDS = ("S-360-12 12V 30A 360W PSU power supply switching enclosed "
            "S-series mains 110 220")
NOTES = """Enclosed S-series switch-mode supply, read from the case label 2026-09-14:

    S-360-12
    AC INPUT  110/220V +/-15%
    DC OUTPUT 12V 30A            (= 360 W)
    CE, ISO9001 SGS PASS

**CHECK THE MAINS SELECTOR BEFORE FIRST POWER-UP.** S-series supplies accept 110 or 220 V through a small SLIDE SWITCH on the case — they do NOT auto-range, and the label reading "110/220V" is exactly what makes people assume they do. Set to 110 and plugged into 220 it fails immediately and destructively. Set to 220 on a 110 V outlet it simply will not start, which is the harmless direction and is routinely misdiagnosed as a dead supply.

This is a property of the FAMILY. Whether this particular unit carries the switch has not been verified — treat it as the first thing to look for, not as an established fact about this unit.

**OUTPUT IS USUALLY TRIMMABLE** on these, via a small pot marked V-ADJ, typically about +/-10% (so roughly 10.8–13.2 V here). Not verified on this unit.

**360 W AT 12 V IS 30 A, AND THE WIRING HAS TO MEAN IT.** At full load that is 10 AWG territory. The screw terminals will happily accept wire far too thin for the rating, and nothing in the supply prevents it.

**NO MAINS CORD IS SUPPLIED** with these, and the AC side is bare screw terminals behind a small cover. It is not a plug-and-play brick.

Sibling of #1160 (S-250-24, 24V 10A), which lives on WS2-S3."""

cat = PartCategory.objects.get(pk=int(
    Part.objects.get(pk=1160).category_id))     # mirror the S-250-24
existing = Part.objects.filter(name=NAME).first()
print(f"category: {cat.pathstring}  (mirrored from #1160)")
print(f"part:     {'EXISTS' if existing else 'will create'}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    print("No stock row: count and location come from Scott.")
    sys.exit(0)

p = existing or Part.objects.create(
    name=NAME, description=DESC, category=cat, keywords=KEYWORDS,
    notes=NOTES, active=True, purchaseable=True, component=True)
p.refresh_from_db()
print(f"\n#{p.pk} {p.name}")
print(f"   mains-selector warning present: {'CHECK THE MAINS SELECTOR' in p.notes}")
print(f"   stock rows {p.stock_items.count()}  <- awaiting count + location")
