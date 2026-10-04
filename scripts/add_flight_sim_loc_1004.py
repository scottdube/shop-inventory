"""Create SLN/Flight Sim, the room location for the X-Plane cockpit, 2026-10-04.

Needed to receive PO-0187 (PNY T400) "at the sim computer to be installed".
Name is Scott's. A ROOM, so never anyone's default_location. Where in the
building it sits was not stated, so the description does not guess.
"""
import os, sys, django
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings"); django.setup()
from stock.models import StockLocation
sln = StockLocation.objects.get(name="SLN", parent=None)
if StockLocation.objects.filter(name__iexact="Flight Sim").exists():
    sys.exit("Flight Sim already exists")
loc = StockLocation(name="Flight Sim", parent=sln, description=(
    "FLIGHT SIM - the X-Plane cockpit and its PCs (FlightSim1, Air Manager). A room, "
    "not a bin: never a default_location. Hardware here is either waiting to be "
    "installed in the sim or a spare kept with it; once installed it is part of the "
    "sim and leaves inventory. Created 2026-10-04 for the T400 GPU (PO-0187)."))
loc.save()
loc = StockLocation.objects.get(pk=loc.pk)
print(f"CREATED loc #{loc.pk} {loc.pathstring}")
