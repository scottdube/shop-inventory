"""B3-R1C3: four distinct switch parts, none of which existed in the catalog.

Deliberately NOT folded into #98 (the white-LED tactile in R1C2) - these are
plain switches, a different part. The 22 loose ones are recorded as a single
'Assorted' line: they are a salvage mix picked by eye from the drawer, not
committed to a layout, so footprint-level identity buys nothing here. That is
the opposite call from the capacitors, and for a reason.
"""
import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

cat = Part.objects.get(pk=98).category
print(f"category: {cat.pathstring if cat else '-'}\n")

NEW = [
    ("Tactile Switch 6x6mm SPST", None,
     "Plain (non-illuminated) 6x6mm through-hole tactile switch.\n\n"
     "Bagged, marked **218J461** — that code matches no catalog part or supplier "
     "SKU, so it is a lot or bin code rather than a traceable part number. "
     "Recorded here in case the same source is used again."),
    ("Adafruit Red 6mm Power Button", "P3104",
     "Adafruit PID **3104** — http://adafru.it/3104\n\n"
     "Bag dated 2016-04-25."),
    ("Adafruit Blue 6mm Power Button", "P3105",
     "Adafruit PID **3105** — http://adafru.it/3105\n\n"
     "Bag dated 2016-04-25."),
    ("Tactile Switch Assorted 6x6", None,
     "Salvage/mixed handful, several types in one bag:\n\n"
     "  ~9  silver body, through-hole, black round plunger\n"
     "  ~8  rectangular black cap\n"
     "   4  on carrier tape, long leads, translucent plunger\n"
     "  1-2 odd (white round cap, grey plunger)\n\n"
     "Kept as ONE part on purpose — picked by eye from the drawer, never "
     "specified into a layout. Split it only if that changes."),
]

for name, ipn, note in NEW:
    p = Part.objects.filter(name=name).first()
    if p:
        print(f"  exists  #{p.pk}  {name}")
        continue
    print(f"  CREATE          {name}" + (f"   IPN={ipn}" if ipn else ""))
    if a.commit:
        p = Part.objects.create(
            name=name[:100], IPN=ipn or "", category=cat,
            description=note.split("\n")[0][:250], notes=note,
            active=True, component=True, purchaseable=True)
        print(f"          -> #{p.pk}")

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
