"""Label rendered as "B07WFKBR4X | Antenna Mag-Mount 978/1090MHz" - the
connector, MCX, fell off the end. Standing at the drawer the question is
what plugs in, not what band it is; a 978/1090 antenna you cannot mate is
no use. Move MCX forward, band moves to the description.

Rejected: a wider template. Template 12 is the shop stock label and changing
it reflows every label already printed.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from part.models import Part

NEW = 'Antenna Mag-Mount MCX, ADS-B'
p = Part.objects.get(pk=388)
print(f"before: {p.name!r} ({len(p.name)})")
p.name = NEW
p.notes = (p.notes or '') + (
    "\n\n2026-09-20 RENAMED from 'Antenna Mag-Mount 978/1090MHz MCX male' (38 chars). "
    "Template 12 prefixes the ASIN, which costs 13 characters, so only ~29 of the name "
    "survives and MCX was cut. The BAND is now description-only; the CONNECTOR is on "
    "the label, because that is the question asked while holding it.")
p.save()
r = Part.objects.get(pk=388)
print(f"after : {r.name!r} ({len(r.name)})  {'OK' if r.name == NEW else 'BAD'}")
