"""Make the LRD Pi / SBC tub a location and record what Scott has said is in it.

Scott, 2026-11-04: "the power supply is in that pie tub, which is currently in
cabinet 6 shelf 4, I guess, but that's probably temporary." A tub is a
container that moves, so it is a location of its own (precedent: the Smart
Switches & Plugs Tub), parented on Cab6-S4 for now; when it moves, re-parent
the tub, not each row. Only the PSU (841) is moved: Scott named only it, and
the Pi 840, microSD 1229 and NESDR 1230 are not assumed to be in there
(TRAPS: a Receiving row is a claim, not goods in hand).
    itq run scripts/pi_tub_cab6s4.py [--commit]"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
shelf = StockLocation.objects.get(pathstring="LRD/Countertop Wall/Cab6/Cab6-S4")
NAME = "Pi / SBC Tub"
DESC = ("Tub for Raspberry Pis / single-board computers and their PSUs, cards and dongles "
        "(STORAGE-PLAN Pi/SBC tub). On Cab6-S4 as of 2026-11-04, probably temporary (Scott); "
        "if it moves, re-parent this location rather than moving rows.")
tub = StockLocation.objects.filter(name=NAME, parent__pathstring__startswith="LRD/").first()
s = StockItem.objects.get(pk=841)
print("tub:", tub.pathstring if tub else f"(new) {shelf.pathstring}/{NAME}", "| 841 @", s.location.pathstring)
assert s.location.pathstring in ("LRD/Receiving",) or (tub and s.location_id == tub.pk)
if "--commit" not in sys.argv:
    raise SystemExit("DRY RUN - add --commit")
if tub is None:
    tub = StockLocation(name=NAME, parent=shelf, description=DESC)
    tub.save()
tub = StockLocation.objects.get(pk=tub.pk)
if s.location_id != tub.pk:
    s.move(tub, "In the Pi / SBC tub on Cab6-S4 (Scott, 2026-11-04)", u)
s = StockItem.objects.get(pk=841)
print(tub.pk, tub.pathstring, "| 841 @", s.location.pathstring)
print("ALL VERIFIED" if s.location_id == tub.pk and tub.parent_id == shelf.pk else "NOT VERIFIED")
