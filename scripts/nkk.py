"""NKK NS-series push buttons - identifiable, so they get their own records.

These come out of the R1C7 'assorted' tray. The maroon ones stay assorted
because nothing is readable on them; these are stamped with a manufacturer and
a part number, so lumping them in would be throwing away information that is
already in hand.
"""
import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

cat = Part.objects.get(pk=98).category
BASE = ("**NKK Switches** (Japan) NS-series miniature push button, panel mount, "
        "rated **3A 125V AC**. Body stamped with NKK's triple-peak mark, the "
        "part number, and `JAPAN`.\n\n"
        "Terminals are marked **N** and **O** (normally-closed / normally-open "
        "positions) - check with a meter before wiring.\n\n"
        "Pulled out of the R1C7 assorted tray because it is stamped and "
        "identifiable, unlike the maroon phenolic buttons alongside it.\n\n")

NEW = [
    ("NKK NS-196 Push Button 3A 125VAC",
     BASE + "Red cap as held. Silver/green body."),
    ("NKK NS-197 Push Button 3A 125VAC",
     BASE + "Black cap as held. Silver/green body. NS-197 is a different "
            "configuration from the NS-196 next to it - do not treat them as "
            "interchangeable without checking the contact arrangement."),
]

for name, note in NEW:
    p = Part.objects.filter(name=name).first()
    if p:
        print(f"  exists  #{p.pk}  {name}")
        continue
    print(f"  CREATE          {name}")
    if a.commit:
        p = Part.objects.create(
            name=name[:100], category=cat,
            description=note.split("\n")[0].replace("**", "")[:250], notes=note,
            active=True, component=True, purchaseable=True)
        print(f"          -> #{p.pk}")

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
