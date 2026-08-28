"""Make the G1000 a sub-build of BO-0006, mirroring BO-0015 Sim Rudder Pedals.

Scott, 2026-08-27: "is G1000 a sub project? If not it should be." It was not —
no build, no part, no location carried the name anywhere in the instance.

Mirrors BO-0015 exactly, because that pattern is already working: an assembly
part in category 132 (assembly + component, not purchaseable), and a Build with
parent=BO-0006 so the sub-build carries its own status and parts list instead of
being invisible inside a simulator that is 'pending' for years.

NO KIT BIN IS CREATED, and that is deliberate. BO-0015 has one (#588, a
Sterilite 6qt on WS2-S4) because its parts were physically gathered. Nothing has
been gathered for the G1000 — the only candidate parts are the two nav switches
whose whereabouts are still unresolved (stock #9). A location in this system is
a PLACE; creating one for a bin that does not exist on a shelf would be a record
that lies about the shop, and an empty named bin is exactly how a kit bin decays
into a parking area. Make the bin when there is something to put in it.

    itq run scripts/add_g1000_subbuild.py            # dry run
    itq run scripts/add_g1000_subbuild.py --commit
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from build.models import Build                                   # noqa: E402
from part.models import Part                                     # noqa: E402

CAT, PARENT_REF = 132, "BO-0006"
NAME = "Sim G1000"
DESC = ("Garmin G1000 glass-cockpit panel for the Cessna flight simulator. "
        "Sub-build of BO-0006. Scope not yet fixed by Scott — created so the "
        "G1000 work has somewhere to hang.")
NOTES = (
    "Sub-build of BO-0006, Cessna Flight Simulator. Created 2026-08-27 at "
    "Scott's request, after a filing question surfaced two nav switches that "
    "were 'either in the mobile cart or used in the G1000 part of the Sim "
    "project' and there was no G1000 anywhere in this system to point at.\n\n"
    "WHY A SUB-BUILD AND NOT A NOTE ON BO-0006: the simulator is a multi-year "
    "pending build. Anything recorded only against it inherits that horizon and "
    "stops being answerable — 'is the G1000 done' has no answer if the G1000 is "
    "a paragraph inside a build that will be pending until the whole sim flies. "
    "BO-0015 Sim Rudder Pedals was split out for the same reason.\n\n"
    "NO KIT BIN YET. BO-0015 has one because its parts were gathered; nothing "
    "has been gathered here. A location in this system is a place, so the bin "
    "gets made when there is something to put in it.\n\n"
    "FIRST CANDIDATE PART: 2x RKJXT1F42001 4-direction navigation switch with "
    "centre push (stock #9) — the right shape for a G1000 FMS control. Whether "
    "they belong to this build is exactly the open question: in the cart they "
    "are stock, fitted to the panel they are consumed by THIS build order.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

parent = Build.objects.get(reference=PARENT_REF)
print(f"parent {parent.reference} {parent.title!r} part=#{parent.part_id}")
for b in Build.objects.filter(parent=parent):
    print(f"  existing sub-build: {b.reference} {b.title}")

if Part.objects.filter(name=NAME).exists() or Build.objects.filter(title=NAME).exists():
    sys.exit(f"!! {NAME!r} already exists — refusing to duplicate")

nxt = max(b.reference_int for b in Build.objects.all()) + 1
ref = f"BO-{nxt:04d}"
print(f"\nwould create part {NAME!r} (cat {CAT}, assembly) and build {ref} "
      f"parent={parent.reference}")

if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

p = Part.objects.create(name=NAME, description=DESC, category_id=CAT,
                        assembly=True, component=True, purchaseable=False,
                        trackable=False, active=True)
Part.objects.filter(pk=p.pk).update(notes=NOTES)
got = Part.objects.get(pk=p.pk)
assert got.assembly and got.component and not got.purchaseable, "flags did not stick"
print(f"OK  part #{p.pk} {got.name}")

b = Build.objects.create(part=p, title=NAME, quantity=1, reference=ref,
                         parent=parent)
Build.objects.filter(pk=b.pk).update(notes=NOTES)
fresh = Build.objects.get(pk=b.pk)
assert fresh.parent_id == parent.pk, "parent did not stick"
assert fresh.part_id == p.pk, "part did not stick"
print(f"OK  build {fresh.reference} parent={fresh.parent.reference} "
      f"status={fresh.get_status_display()}")
print("\nsub-builds of BO-0006 now:")
for s in Build.objects.filter(parent=parent).order_by("reference"):
    print(f"  {s.reference}  {s.title}")
