"""Build the 35 shelf and drawer locations on the LRD bench wall.

Scott approved 2026-10-19: Cab5-Cab8 S1-S5 (4 adjustable shelves + the cabinet
floor, numbered from the TOP down; S5 is always the floor) and Cab2-Cab4 D1-D5
(top two drawers 2.25 in deep, lower three 6 in; inside 24.25 W x 18.5 D).
Cab8 is built too, although the draft zoning has it as house overflow. Scott
chose all 35, and an unused location costs nothing.

structural=False: they have to hold stock. Names are globally unique because
BinScan's resolve_loc() refuses an ambiguous name; the clash check enforces it.
Created top-down per cabinet so creation-pk order (BinScan's sort) is also
physical order.

Dry run by default; --commit writes and re-reads.
"""
import os, sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
WALL_PK = 524
UPPERS = {525: "Cab5", 526: "Cab6", 527: "Cab7", 528: "Cab8"}
BANKS = {530: "Cab2", 531: "Cab3", 532: "Cab4"}

PLAN = []  # (parent, name, description)
for pk, cab in BANKS.items():
    for d in range(1, 6):
        kind = ("shallow drawer, inside 24.25 W x 18.5 D x 2.25 H in" if d <= 2
                else "deep drawer, inside 24.25 W x 18.5 D x 6 H in")
        PLAN.append((pk, f"{cab}-D{d}",
                     f"{cab} drawer {d} of 5, numbered from the TOP down: {kind}."))
for pk, cab in UPPERS.items():
    for s in range(1, 6):
        what = ("the cabinet FLOOR (fixed)" if s == 5
                else f"adjustable shelf {s} of 4, 14 D x 26.5 W in")
        PLAN.append((pk, f"{cab}-S{s}",
                     f"{cab} level {s} of 5, numbered from the TOP down: {what}. "
                     "Shelves are adjustable, so clear height depends on spacing."))
assert len(PLAN) == 35

parents = {pk: StockLocation.objects.get(pk=pk) for pk in {**UPPERS, **BANKS}}
for pk, p in parents.items():
    assert p.parent_id == WALL_PK and p.name == {**UPPERS, **BANKS}[pk], (pk, p.pathstring)

clash = StockLocation.objects.filter(name__in=[n for _, n, _ in PLAN])
if clash.exists():
    sys.exit("REFUSED, name already in use: "
             + ", ".join(f"{l.pathstring} [pk {l.pk}]" for l in clash))

for parent, name, desc in PLAN:
    print(f"{'CREATE' if COMMIT else 'would '} {parents[parent].pathstring}/{name}")
if not COMMIT:
    print(PLAN[0][2]); print(PLAN[-1][2])
    sys.exit()

made = []
for parent, name, desc in PLAN:
    loc = StockLocation.objects.create(parent=parents[parent], name=name,
                                       description=desc, structural=False)
    made.append((loc.pk, parent, name, desc))

bad = 0
for pk, parent, name, desc in made:
    loc = StockLocation.objects.get(pk=pk)
    ok = (loc.name == name and loc.parent_id == parent and loc.description == desc
          and not loc.structural and loc.pathstring == f"{parents[parent].pathstring}/{name}")
    bad += not ok
    if not ok:
        print(f"  BAD pk {pk} {loc.pathstring}")
print(f"created pk {made[0][0]}-{made[-1][0]}")
print("ALL 35 VERIFIED" if not bad else f"{bad} BAD")
