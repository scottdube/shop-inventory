"""B3-R1C4: three distinct toggle switch parts.

The C&K lot is kept as one 'assorted' record even though these ARE traceable
parts, because it is a mixed salvage handful spanning several C&K series and
functions. If one is ever specified into a design, read the part number off the
body - the note says so. That is the compromise between the capacitor rule
(footprint is identity) and not creating twelve records for a bag of twelve.
"""
import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

cat = Part.objects.get(pk=98).category   # Switches

NEW = [
    ("Toggle Switch Sub-Miniature 3A 250V", "",
     "Sub-miniature toggle, blue body, marked 3A 250V. Bagged loose.\n\n"
     "Smallest of the three toggle types in this drawer. Exact series not "
     "identified - no packaging survived."),
    ("MTS-101 Mini Toggle Switch 2-Pin SPST", "B0799LBFNY",
     "MTS-101, 2-pin SPST ON/OFF miniature toggle, blue body, 6A 125V AC.\n\n"
     "Amazon ASIN **B0799LBFNY**, sold as a **10 pack**, with mounting nuts and "
     "washers in the bag. Original packaging retained."),
    ("C&K Miniature Toggle Switch, Assorted", "",
     "Mixed lot of **C&K USA** miniature toggles - the quality ones, not clones.\n\n"
     "Visible markings include **7101** and **7901** series, red and mint bodies, "
     "2- and 3-pin, several marked **MOM** (momentary) with 3A 250VAC / 5A 125VAC "
     "ratings. Some have gold-plated pins.\n\n"
     "Kept as ONE record because it is a salvage mix spanning several series and "
     "functions. **If you specify one into a design, read the part number off the "
     "body** - do not rely on this record for pinout or function.\n\n"
     "Two toggle boots (one white, one yellow) are in the drawer as well."),
]

for name, ipn, note in NEW:
    p = Part.objects.filter(name=name).first()
    if p:
        print(f"  exists  #{p.pk}  {name}")
        continue
    print(f"  CREATE          {name}" + (f"   IPN={ipn}" if ipn else ""))
    if a.commit:
        p = Part.objects.create(
            name=name[:100], IPN=ipn, category=cat,
            description=note.split("\n")[0].replace("**", "")[:250], notes=note,
            active=True, component=True, purchaseable=True)
        print(f"          -> #{p.pk}")

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
