"""Rename the LRD bench-wall cabinets to the installer's numbers: Cab1..Cab8.

Installer render (docs/lrd/bench-wall-installer-render.png): 1 door base cabinet,
2-4 drawer banks, 5-8 uppers, 9 worktop (not a location). The prints Scott is
fetching use those numbers, so InvenTree uses them too.

Dry run by default; --commit writes. Every write is re-read (silent-save trap).
"""
import os, sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockLocation, StockItem  # noqa: E402

COMMIT = "--commit" in sys.argv
CONFIRM = "confirm against the prints before building"

PLAN = {
    529: ("Cab1", "Installer #1. Base cabinet at the left of the run, single tall door. "
                  "**Contents and internal shelving not yet known** -- enumerate on site."),
    530: ("Cab2", "Installer #2. Drawer bank 1 of 3 in the base run, left to right. "
                  "5 drawers per the installer render and 2026-10-19 photos; " + CONFIRM +
                  " Cab2-D1, D2 ... numbered from the TOP down."),
    531: ("Cab3", "Installer #3. Drawer bank 2 of 3 in the base run, left to right. "
                  "5 drawers per the installer render and 2026-10-19 photos; " + CONFIRM +
                  " Cab3-D1, D2 ... numbered from the TOP down."),
    532: ("Cab4", "Installer #4. Drawer bank 3 of 3 in the base run, left to right. "
                  "5 drawers per the installer render and 2026-10-19 photos; " + CONFIRM +
                  " Cab4-D1, D2 ... numbered from the TOP down."),
    525: ("Cab5", "Installer #5. Upper cabinet 1 of 4, left to right. Two doors, adjustable "
                  "shelves; 2026-10-19 photos show 3 shelves + floor -- " + CONFIRM +
                  " Cab5-S1, S2 ... numbered from the TOP down."),
    526: ("Cab6", "Installer #6. Upper cabinet 2 of 4, left to right. Two doors, adjustable "
                  "shelves; 2026-10-19 photos show 3 shelves + floor -- " + CONFIRM +
                  " Cab6-S1, S2 ... numbered from the TOP down."),
    527: ("Cab7", "Installer #7. Upper cabinet 3 of 4, left to right. Two doors, adjustable "
                  "shelves; 2026-10-19 photos show 3 shelves + floor -- " + CONFIRM +
                  " Cab7-S1, S2 ... numbered from the TOP down."),
    528: ("Cab8", "Installer #8. Upper cabinet 4 of 4, left to right (next to the house "
                  "door). Two doors, adjustable shelves; 2026-10-19 photos show 3 shelves + "
                  "floor -- " + CONFIRM + " Cab8-S1, S2 ... numbered from the TOP down."),
}
WALL_PK = 524
WALL_ADD = (" Cabinets carry the installer's numbers Cab1-Cab8 (2026-10-19); 9 is the "
            "worktop and is not a location. Render: docs/lrd/bench-wall-installer-render.png.")

# Refuse if any target name already exists elsewhere -- names are not unique
# in InvenTree and BinScan refuses an ambiguous name.
clash = StockLocation.objects.filter(name__in=[n for n, _ in PLAN.values()]).exclude(pk__in=PLAN)
if clash.exists():
    sys.exit("REFUSED, name already in use: " + ", ".join(f"{l.pathstring} [pk {l.pk}]" for l in clash))

for pk, (name, desc) in PLAN.items():
    loc = StockLocation.objects.get(pk=pk)
    assert loc.parent_id == WALL_PK, (pk, loc.pathstring)
    assert StockItem.objects.filter(location=loc).count() == 0, f"{loc.name} holds stock"
    print(f"{'WRITE' if COMMIT else 'would'} pk {pk}: {loc.name} -> {name}")
    if COMMIT:
        loc.name = name
        loc.description = desc
        loc.save()

wall = StockLocation.objects.get(pk=WALL_PK)
if "installer's numbers" not in wall.description:
    print(f"{'WRITE' if COMMIT else 'would'} append installer note to {wall.pathstring}")
    if COMMIT:
        wall.description = wall.description + WALL_ADD
        wall.save()

if COMMIT:
    print("\nre-read:")
    bad = 0
    for pk, (name, desc) in PLAN.items():
        loc = StockLocation.objects.get(pk=pk)
        ok = loc.name == name and loc.description == desc and loc.pathstring.endswith("/" + name)
        bad += not ok
        print(f"  {'OK ' if ok else 'BAD'} pk {pk} {loc.pathstring}")
    w = StockLocation.objects.get(pk=WALL_PK)
    ok = "installer's numbers" in w.description
    bad += not ok
    print(f"  {'OK ' if ok else 'BAD'} pk {WALL_PK} wall description")
    print("ALL VERIFIED" if not bad else f"{bad} NOT WRITTEN")
