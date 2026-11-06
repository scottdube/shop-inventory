"""Create the LRD tub that holds the HOT club Info Orbs kit stock (2026-11-06).

Club parts are bought on ordinary POs and received here, then allocated to a club
build order (37 kits). Kept apart from Scott's drawers so the club's parts never
read as his spares; whatever is left after hand-out becomes ordinary stock.

Parent is LRD/Countertop Wall, not LRD/Electronics Bench as first proposed: the
new bench is still on order (374930), so a location under it would claim a place
that does not exist yet. Move the tub's parent when the bench lands.

Dry run by default.  itq run scripts/club_orbs_tub.py [--commit]"""
import os, sys
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django; django.setup()
from stock.models import StockLocation

PARENT, NAME = "LRD/Countertop Wall", "HOT Info Orbs Club Tub"
DESC = "HOT club Info Orbs kit parts (37 kits, hand-out 2026-11-24). Club stock, not Scott's spares."
parent = StockLocation.objects.get(pathstring=PARENT)
have = StockLocation.objects.filter(parent=parent, name=NAME).first()
print(f"{PARENT}/{NAME}: {'exists #%d' % have.pk if have else 'to create'}")
if "--commit" not in sys.argv:
    print("DRY RUN - nothing written"); sys.exit(0)
if not have:
    have = StockLocation(parent=parent, name=NAME, description=DESC, structural=False)
    have.save()
loc = StockLocation.objects.get(pk=have.pk)
ok = loc.pathstring == f"{PARENT}/{NAME}" and loc.description == DESC and not loc.structural
print(f"#{loc.pk} {loc.pathstring}")
print("VERDICT:", "SUCCESS" if ok else "FAILED")
