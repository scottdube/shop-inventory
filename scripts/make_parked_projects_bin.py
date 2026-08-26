"""A bin for parts that belong to a PAUSED project and have no generic home.

Scott 2026-08-26: "should probably start a separate tub or clear storage bin
for that kind of stuff because there's gonna be more of it as we get further
into the wire shelves."

The prompting case is a motorcycle steering damper bought for the rudder pedals
of the Cessna flight simulator (#832), a project still live but not worked in a
while. It is not general shop stock — nothing else in the shop wants a steering
damper — and it is not a kit being actively built, so neither the red-bin rule
nor a wall drawer fits it.

THE RULE, because this is exactly the kind of bin that becomes a junk drawer:

  IN:  a part bought FOR A NAMED PROJECT that is paused, where the part has no
       generic use. Every item must name its project. If you cannot name one,
       it does not belong here.

  OUT: anything with a generic home. The R8-2RS bearings came off the same
       shelves and went to Bearings & Motion, because a bearing is a bearing
       whatever it was bought for.

  OUT: "I don't know what this is." That is A2-R8C8, the PRE-SORT QUEUE, and
       conflating the two is how this bin dies. A parked-project part has a
       known owner; a pre-sort part has an unknown identity.

WHEN ONE PROJECT OUTGROWS THIS, IT GETS ITS OWN BIN. This is deliberately one
tub for several projects until the volume argues otherwise — Scott expects more
as the wire shelves are worked, and splitting on the first item would be
guessing at the shape.

Sited on WS2-S4 with Adhesives and Bearings & Motion. The bin is the location,
so moving it later is a re-parent.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

SHELF, BIN_PART, CAT = 456, 1089, 137

DESC = (
    "PARKED PROJECTS. Parts bought for a NAMED project that is paused, which "
    "have no generic use elsewhere. Sterilite 6qt clear, snap-on lid, on "
    "WS2-S4. A HOME — things filed here get it as default_location. The BIN is "
    "the location, so moving it to another shelf is a re-parent, not a rename. "
    "Established 2026-08-26.\n\n"
    "THE RULE, because this is the kind of bin that becomes a junk drawer:\n\n"
    "IN — a part bought for a named, paused project, with no generic use. "
    "EVERY ITEM MUST NAME ITS PROJECT. If you cannot name one, it does not "
    "belong here.\n\n"
    "OUT — anything with a generic home. The R8-2RS bearings came off the same "
    "wire shelves the same afternoon and went to Bearings & Motion, because a "
    "bearing is a bearing whatever it was bought for.\n\n"
    "OUT — 'I don't know what this is'. That is A2-R8C8, the PRE-SORT QUEUE. "
    "Conflating the two is how this bin dies: a parked-project part has a KNOWN "
    "OWNER and an unknown schedule; a pre-sort part has an unknown identity.\n\n"
    "ONE TUB FOR SEVERAL PROJECTS until volume argues otherwise. Scott expects "
    "more as the wire shelves are worked; splitting on the first item would be "
    "guessing at the shape.")

NAME = "Steering Damper, CNC adjustable 10 in (INNOGLOW)"
PDESC = ("Motorcycle steering damper, CNC aluminium, 10 in, adjustable damping. "
         "Bought for the rudder pedals of the Cessna flight simulator.")
PNOTES = (
    "FOR THE CESSNA FLIGHT SIMULATOR (#832) — rudder pedals. Scott, "
    "2026-08-26: the project is still live but has not been worked in a "
    "while.\n\n"
    "A steering damper on rudder pedals gives them the resistance and settling "
    "a real aircraft has; a spring alone would oscillate. The damping knob is "
    "the point of choosing this over a fixed strut.\n\n"
    "ARRIVES ON A GREEN 3D-PRINTED MOUNT, shop-made, held by a socket head "
    "screw. That mount is part of the pedal design and is NOT catalogued as its "
    "own part — it is a print, remakeable from the model, and the model is the "
    "thing worth not losing. Do not strip it off to 'tidy' the damper.\n\n"
    "PURCHASED: Amazon 2024-06-09, 'INNOGLOW Motorcycle Steering Damper Control "
    "Universal CNC Black 10\" Adjustable Stabilizer For Suzuki Kawasaki Street "
    "bikes'.\n\n"
    "NOT general stock. Nothing else in this shop wants a steering damper, "
    "which is why it is in Parked Projects rather than Bearings & Motion.")

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
shelf = StockLocation.objects.get(pk=SHELF)
existing = StockLocation.objects.filter(name="Parked Projects", parent=shelf).first()
print(f"bin: {'EXISTS ' + str(existing.pk) if existing else 'to create'} under {shelf.name}")
print(f"seed: 1 x {NAME}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

binloc = existing or StockLocation.objects.create(
    name="Parked Projects", parent=shelf, description=DESC)
StockLocation.objects.filter(pk=binloc.pk).update(description=DESC)
print(f"location [{binloc.pk}] {binloc.pathstring}")

stack = StockItem.objects.filter(part_id=BIN_PART).first()
if stack and "Parked Projects" not in (stack.notes or ""):
    stack.take_stock(1, user, notes="One bin taken to become PARKED PROJECTS on WS2-S4, 2026-08-26.")
    stack.refresh_from_db()
    StockItem.objects.filter(pk=stack.pk).update(notes=(stack.notes or "").rstrip() +
        "\n\n2026-08-26: one bin consumed to become PARKED PROJECTS on WS2-S4.")

p = Part.objects.filter(name=NAME).first()
if not p:
    p = Part.objects.create(name=NAME, description=PDESC, category_id=CAT,
                            default_location=binloc, purchaseable=True, active=True)
    print(f"part [{p.pk}] created")
Part.objects.filter(pk=p.pk).update(notes=PNOTES, default_location=binloc)

si = StockItem.objects.filter(part=p, location=binloc).first()
if not si:
    si = StockItem.objects.create(part=p, location=binloc, quantity=1)
StockItem.objects.filter(pk=si.pk).update(
    notes="Counted 1 on the bench 2026-08-26, on its printed mount. One order, "
          "one unit, 2024-06-09.")

sim = Part.objects.get(pk=832)
if "steering damper" not in (sim.notes or "").lower():
    Part.objects.filter(pk=832).update(notes=(sim.notes or "").rstrip() +
        f"\n\nRUDDER PEDALS, paused. Scott 2026-08-26: the rudder pedal work is "
        f"part of this project, still live, not worked in a while. The steering "
        f"damper bought for it (#{p.pk}, Amazon 2024-06-09) is in the Parked "
        f"Projects bin on WS2-S4, on its shop-printed green mount.\n\n"
        f"This record's description says it exists to CLAIM parts already "
        f"consumed by a finished build. That is now only half true — the rudder "
        f"pedals are unfinished, so the project has both a past and a backlog.")

print(f"\n{binloc.pathstring}")
for s in StockItem.objects.filter(location=binloc):
    print(f"  {s.quantity:g} x {s.part.name}")
print(f"empty Sterilite bins left: "
      f"{sum(float(s.quantity) for s in StockItem.objects.filter(part_id=BIN_PART)):g}")
