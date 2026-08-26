"""BO for the sim rudder pedals, as a CHILD of the simulator build. Rename the tub.

Scott 2026-08-26: "create a new bo for the rudder pedals can it be a sub order
of the simulator? And change the name of the tub from parked proj to the build
order Sim Rudder Pedals".

Yes -- InvenTree's Build model has a `parent`, so this is a real sub-build and
not a naming convention. BO-0006 (Cessna Flight Simulator, part #832) becomes
the parent; the rudder pedals get their own reference, status and notes while
still rolling up.

THIS CHANGES WHAT THE TUB IS, an hour after it was created. It was "Parked
Projects", a general home for parts of any paused project, with an admission
rule written to stop it becoming a junk drawer. It is now ONE BUILD ORDER'S KIT:
the bin is the rudder pedals and nothing else.

That is a better model and it costs the thing it was made for. Scott's original
observation stands -- "there's gonna be more of it as we get further into the
wire shelves" -- so the general tub is DEFERRED, not abandoned. When the second
paused project's parts surface with nowhere to go, that bin gets made and the
admission rule is preserved below, ready to use.

Two labels printed minutes ago are now wrong and must be discarded: the bin's
own ("Parked Projects", QL810W-54) and the damper's, whose footer carries the
bin name ("Parked Projects · Mechanical", QL810W-55). A part label showing its
location means renaming a bin invalidates every label in it -- cheap here with
one part, and worth knowing before a full bin gets renamed.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part
from build.models import Build
from stock.models import StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
parent = Build.objects.get(reference="BO-0006")
binloc = StockLocation.objects.get(pk=588)
print(f"parent build: {parent.reference} {parent.part.name}")
print(f"bin: {binloc.name} -> Sim Rudder Pedals")

PARTNAME = "Sim Rudder Pedals"
PARTDESC = ("Rudder pedal assembly for the Cessna flight simulator. Sub-build "
            "of BO-0006. Paused — parts gathered, not built.")
PARTNOTES = (
    "SUB-BUILD OF THE CESSNA FLIGHT SIMULATOR (#832 / BO-0006).\n\n"
    "Scott 2026-08-26: the simulator is still live but has not been worked in a "
    "while, and the rudder pedals are the unfinished part of it. Given its own "
    "build order so the pedals have a status, a parts list and a home that do "
    "not depend on the whole simulator moving.\n\n"
    "KNOWN DESIGN INTENT so far: a motorcycle steering damper (#1129) gives the "
    "pedals resistance and settling. A spring alone would oscillate; the "
    "adjustable damping knob is the reason that part was chosen over a fixed "
    "strut. It sits on a shop-printed green mount which is part of the design "
    "and is not separately catalogued — the MODEL is the thing worth not "
    "losing.\n\n"
    "The bin on WS2-S4 is this build's kit and carries its name.")

BINDESC = (
    "SIM RUDDER PEDALS — the kit for that build order, a sub-build of BO-0006 "
    "(Cessna Flight Simulator). Sterilite 6qt clear, snap-on lid, on WS2-S4. "
    "The BIN is the location and the name travels with it, so moving shelves is "
    "a re-parent. Established 2026-08-26 as 'Parked Projects' and renamed the "
    "same day.\n\n"
    "ONE BUILD ORDER'S KIT, not a general parking area. If a part in here does "
    "not belong to the rudder pedals, it is in the wrong bin.\n\n"
    "THE GENERAL TUB THIS WAS FIRST MADE AS IS DEFERRED, NOT ABANDONED. Scott, "
    "on why it was started: \"there's gonna be more of it as we get further "
    "into the wire shelves.\" When a second paused project's parts surface with "
    "nowhere to go, make that bin and use the rule written for it:\n\n"
    "  IN — bought for a NAMED, paused project, with no generic use. Every item "
    "must name its project; if you cannot name one it does not belong.\n"
    "  OUT — anything with a generic home. A bearing is a bearing whatever it "
    "was bought for.\n"
    "  OUT — 'I don't know what this is'. That is A2-R8C8, the pre-sort queue. "
    "A parked-project part has a KNOWN OWNER and an unknown schedule; a "
    "pre-sort part has an unknown identity.")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

p = Part.objects.filter(name=PARTNAME).first()
if not p:
    p = Part.objects.create(name=PARTNAME, description=PARTDESC, category_id=132,
                            assembly=True, purchaseable=False, active=True)
    print(f"part [{p.pk}] created")
Part.objects.filter(pk=p.pk).update(notes=PARTNOTES, default_location=binloc)

b = Build.objects.filter(part=p).first()
if not b:
    b = Build.objects.create(part=p, title="Sim Rudder Pedals", quantity=1,
                             parent=parent, issued_by=user)
    print(f"build {b.reference} created")
Build.objects.filter(pk=b.pk).update(notes=(
    "Sub-build of BO-0006, Cessna Flight Simulator. Created 2026-08-26 at "
    "Scott's request so the rudder pedals carry their own status and parts list "
    "rather than being invisible inside a simulator that is 'done'.\n\n"
    "PAUSED, not stalled for a reason anyone recorded. Parts are being gathered "
    "off the wire shelves; the kit bin on WS2-S4 carries this build's name."))

# rename the bin: .save(), not .update() -- pathstring is derived in save()
binloc.name = "Sim Rudder Pedals"
binloc.save()
StockLocation.objects.filter(pk=588).update(description=BINDESC)
binloc.refresh_from_db()

# and the simulator part should point at the child
sim = Part.objects.get(pk=832)
if b.reference not in (sim.notes or ""):
    Part.objects.filter(pk=832).update(notes=(sim.notes or "").rstrip() +
        f"\n\nSUB-BUILD: {b.reference} SIM RUDDER PEDALS (part #{p.pk}), created "
        f"2026-08-26 as a child of BO-0006. The pedals are the unfinished half "
        f"of this project and now have their own status, parts list and kit bin "
        f"instead of being invisible inside a build recorded as assembled.")

print(f"\nbuild {b.reference} parent={b.parent.reference} part={b.part.pk} {b.part.name}")
print(f"bin [{binloc.pk}] {binloc.name}")
print(f"pathstring: {binloc.pathstring}")
stale = StockLocation.objects.filter(pathstring__icontains="Parked Projects").count()
print(f"locations still pathed 'Parked Projects': {stale}")
