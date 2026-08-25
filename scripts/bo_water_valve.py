"""Build order for the Motorized Water Shutoff Valve prototype (RB-24).

Scott said yes on 2026-08-25. Follows the house shape exactly: an assembly Part
in Projects (assembly=True, not purchaseable, not a component), then a Build
against it at status 10 / Pending, quantity 1.

BOM carries ONLY the servo. The 3D printed mounting parts are deliberately not
on it: they have no part record, because a prototype print is the state of an
experiment rather than stock. When the geometry settles, the print becomes a
part and joins the BOM -- and adding a BOM line later is safe HERE precisely
because the build is not complete; completing one freezes its line items.
"""
import os, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part, PartCategory, BomItem
from build.models import Build

COMMIT = "--commit" in sys.argv
TODAY = date.today()
user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()

NAME = "Motorized Water Shutoff Valve"
DESC = ("Prototype: a 35KG coreless digital servo turning a water shutoff "
        "valve, on 3D printed mounting parts. Servo horn and ball link already "
        "fitted. Kit lives in RB-24. Prints are prototypes and carry no part "
        "record yet - the geometry is still moving.")
TITLE = "Motorized Water Shutoff Valve prototype"

dupes = Part.objects.filter(name__icontains="shutoff") | Part.objects.filter(name__icontains="shut off")
print(f"duplicate check: {dupes.count()}")
for p in dupes:
    print(f"  #{p.pk} {p.name}")

print(f"\nwould create part {NAME!r} in Projects, assembly=True")
print(f"  BOM: 1 x #242 ANNIMOS 35KG servo")
print(f"  build: {TITLE!r}, qty 1, status 10 (Pending)")

if not COMMIT:
    print("\n  DRY RUN - add --commit")
    sys.exit()

part = Part.objects.filter(name=NAME).first()
if part is None:
    part = Part.objects.create(
        name=NAME, description=DESC,
        category=PartCategory.objects.get(pathstring="Projects"),
        assembly=True, component=False, purchaseable=False, active=True)
    print(f"created part #{part.pk}")

servo = Part.objects.get(pk=242)
if not BomItem.objects.filter(part=part, sub_part=servo).exists():
    BomItem.objects.create(part=part, sub_part=servo, quantity=1,
                           note="One servo, counted in RB-24 2026-08-25.")

build = Build.objects.filter(part=part).first()
if build is None:
    build = Build.objects.create(part=part, title=TITLE, quantity=1,
                                 issued_by=user, status=10)
    print(f"created {build.reference}")

part = Part.objects.get(pk=part.pk)
build = Build.objects.get(pk=build.pk)
bom = BomItem.objects.filter(part=part).count()
ok = part.assembly and bom == 1 and build.quantity == 1 and build.part_id == part.pk
print(f"\n  part #{part.pk} assembly={part.assembly} BOM lines={bom}")
print(f"  {build.reference} '{build.title}' qty={build.quantity:g} status={build.status}")
print("  VERIFIED" if ok else "  MISMATCH - stop and look")
