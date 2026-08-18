"""Split the C&K lot by FUNCTION, which is how Scott actually distinguished them.

Not by series or body colour - by whether the toggle stays where you put it.
Momentary vs maintained is the choice you make at design time, so it earns two
records where 'assorted' would have hidden it.

Both are SPDT: 3 legs, common in the middle, ON to either side. Explicitly NOT
double-pole - Scott checked.
"""
import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

COMMON = ("Mixed lot of **C&K USA** miniature toggles - the quality ones, not "
          "clones. Markings seen include **7101** and **7901** series; red and "
          "mint bodies; some with gold-plated pins.\n\n"
          "**SPDT, 3 legs** - common in the middle, ON to either side. "
          "Single pole, not double - verified by hand 2026-08-17.\n\n"
          "**If you specify one into a design, read the part number off the "
          "body** - this record is good for 'do I have one', not for pinout.\n\n")

p = Part.objects.get(pk=744)
print(f"  rename #744  {p.name}")
print(f"      -> C&K Miniature Toggle Switch SPDT ON-ON")
if a.commit:
    p.name = "C&K Miniature Toggle Switch SPDT ON-ON"
    p.description = "C&K USA miniature toggle, SPDT ON-ON, maintained (stays put), 3 leg"[:250]
    p.notes = (COMMON + "**Maintained** - stays where you put it. Rated 3A 250VAC "
               "/ 5A 125VAC.\n\nTwo toggle boots (white, yellow) are loose in this "
               "drawer as well.")
    p.save()

name = "C&K Miniature Toggle Switch SPDT Momentary"
q = Part.objects.filter(name=name).first()
if q:
    print(f"  exists #{q.pk}  {name}")
else:
    print(f"  CREATE       {name}")
    if a.commit:
        q = Part.objects.create(
            name=name, category=p.category,
            description="C&K USA miniature toggle, SPDT momentary, springs back, 3 leg"[:250],
            notes=(COMMON + "**Momentary** - springs back to centre/off when "
                   "released. Body marked **MOM**, rated 3A 250VAC / 5A 125VAC."),
            active=True, component=True, purchaseable=True)
        print(f"          -> #{q.pk}")

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
