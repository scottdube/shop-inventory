"""Arrowmax cordless engraving pen kit -- make sure it is in inventory, then commute it.

Scott, 2026-10-10, with a photo of the open box: "Make sure its in inventory
make it a commuter."

From the photo: Arrowmax ("AM", "Ultimate Professional Products") gift box;
aluminium pen-style cordless rotary engraver with a knurled collet nut; a
tray of small diamond burrs (cylinders, cones, balls, needles) in an orange
foam strip; a USB-A charge cable. No model number, voltage or burr shank size
is visible, and none is asserted here. The burr count is NOT recorded from
the photo -- count the tray before trusting a number.

Written from a cloud session that cannot reach the Mini, so it checks before
it creates:

  1. Search for an existing part (Arrowmax / engraving pen / engraver /
     diamond burr). An importer may already have it from an order email.
     Found -> print it and its stock rows, create nothing.
  2. Not found -> create the part and one stock row at --loc (required;
     Scott has not said where it lives).

Category: Equipment/Hand Tools -- the handheld-tool home the crimpers use
(sweep_0901_1640.py). No PO, no price: purchase history unknown.

    itq run scripts/add_arrowmax_engraver.py                     # search only
    itq run scripts/add_arrowmax_engraver.py --loc BL-D3         # dry run create
    itq run scripts/add_arrowmax_engraver.py --loc BL-D3 --commit
    itq run scripts/trip.py mark <SI pk> "engraving pen, one only, carry both ways"
"""
import argparse
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--loc", default=None, help="StockLocation name where the kit lives")
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

TERMS = ["arrowmax", "arrow max", "engraving pen", "engraver pen", "engraving tool",
         "diamond burr", "cordless engraver", "mini engraver"]
q = Q()
for t in TERMS:
    q |= Q(name__icontains=t) | Q(keywords__icontains=t) | Q(description__icontains=t)
hits = list(Part.objects.filter(q))

if hits:
    print(f"FOUND {len(hits)} candidate part(s) -- creating nothing:")
    for p in hits:
        print(f"  part #{p.pk} {p.name}  [{p.category.pathstring if p.category else '-'}]")
        for s in StockItem.objects.filter(part=p).select_related("location"):
            com = "commutes" if (s.metadata or {}).get("commutes") else ""
            print(f"      SI #{s.pk} qty={float(s.quantity):g} "
                  f"@ {s.location.pathstring if s.location else 'NO LOCATION'} {com}")
    print("\nIf one is this kit:  itq run scripts/trip.py mark <SI pk> "
          "\"engraving pen, one only, carry both ways\"")
    sys.exit(0)

print("no existing part matches", TERMS)
if not args.loc:
    sys.exit("give --loc <location name> to create it (Scott has not said where it lives)")

locs = list(StockLocation.objects.filter(name__iexact=args.loc))
if len(locs) != 1:
    pre = args.loc.split("-")[0]
    print(f"!! location {args.loc!r}: {len(locs)} matches; names starting {pre}:",
          list(StockLocation.objects.filter(name__istartswith=pre).values_list("pk", "name")[:40]))
    sys.exit(1)
loc = locs[0]
cat = PartCategory.objects.get(name="Hand Tools", parent__name="Equipment")
print(f"location #{loc.pk} {loc.pathstring} | category #{cat.pk} {cat.pathstring}")

SPEC = dict(
    name="Arrowmax Cordless Engraving Pen Kit, diamond burrs",
    description="Pen-style cordless rotary engraver, USB-charged, with a tray of "
                "diamond burrs (cylinder, cone, ball, needle)",
    keywords="engraving pen, engraver, rotary tool, micro rotary, cordless, diamond burr, "
             "bit set, carving, etching, Arrowmax, AM, USB rechargeable",
    category=cat, component=False, purchaseable=True, assembly=False,
    default_location=loc,
    notes=("Identified from Scott's photo of the open box, 2026-10-10.\n\n"
           "Contents seen: Arrowmax gift box; aluminium pen body with knurled "
           "collet nut; tray of diamond burrs in an orange foam strip; USB-A "
           "charge cable.\n\n"
           "**Not recorded, because not visible:** model number, voltage/RPM, "
           "collet/shank size, burr count. Read them off the pen or the box "
           "underside; count the tray.\n\n"
           "**Commutes SLN <-> LRD** -- one kit, carried both ways (trip.py)."),
)
assert len(SPEC["name"]) <= 100 and len(SPEC["description"]) <= 250 and len(SPEC["keywords"]) <= 250

if not args.commit:
    sys.exit("\nDRY RUN -- add --commit")

p = Part(**SPEC)
p.save()
p.refresh_from_db()
assert p.name == SPEC["name"] and p.category_id == cat.pk, "part did not stick"
print(f"CREATED part #{p.pk} {p.name}")

s = StockItem(part=p, location=loc, quantity=1,
              notes="Filed 2026-10-10 from Scott's photo; one kit seen.")
s.save()
s.refresh_from_db()
assert s.location_id == loc.pk and float(s.quantity) == 1, "stock did not stick"
print(f"CREATED SI #{s.pk} @ {loc.pathstring}")

print("\nNEXT:")
print(f'  itq run scripts/trip.py mark {s.pk} "engraving pen, one only, carry both ways"')
print(f"  itq run scripts/print_part_label.py {s.pk} --stockitem     # render; add --print")
