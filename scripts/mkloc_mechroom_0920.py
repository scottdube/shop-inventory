#!/usr/bin/env python3
"""Create SLN/Mechanical Room — a BUILDING SPACE, not a storage bin.

Created 2026-09-20 when the UniFi nanoHD (PO-0175) was installed there. Until
now the location tree modelled only places things are STORED; an access point
screwed to a ceiling is neither in a drawer nor missing, and booking it to a bin
would have said it was on a shelf. SLN/Garage set the precedent that a room can
be a location.

Nothing here is ever a default_location: a default is where a SPARE goes home,
and everything in this room is in service.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockLocation

DESC = (
    "MECHANICAL ROOM — a room in the building, not a storage bin. Holds "
    "INSTALLED infrastructure that is in service: network gear, controls, "
    "anything mounted and wired. Stock here is an asset register entry, not "
    "something you can go pick. NOTHING HERE IS EVER A default_location — a "
    "default is where a spare goes home, and nothing in this room is spare. "
    "Established 2026-09-20 with the UniFi nanoHD AP from PO-0175."
)

sln = StockLocation.objects.get(pk=1)
existing = StockLocation.objects.filter(parent=sln, name="Mechanical Room")
if existing.exists():
    loc = existing.get()
    print(f"already exists: pk={loc.pk} {loc.pathstring!r}")
else:
    loc = StockLocation.objects.create(parent=sln, name="Mechanical Room", description=DESC)
    print(f"created pk={loc.pk}")

# Verify the write landed (this install has reported success and written nothing)
loc = StockLocation.objects.get(pk=loc.pk)
assert loc.pathstring == "SLN/Mechanical Room", loc.pathstring
assert loc.description == DESC, "description did not stick"
print(f"VERIFIED pk={loc.pk} {loc.pathstring!r}")
