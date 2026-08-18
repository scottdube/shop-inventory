"""B3-R1C7: momentary push buttons - one bagged product, one salvage tray."""
import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

cat = Part.objects.get(pk=98).category

NEW = [
    ("PBS-110-BK Momentary Push Button NO", "X002B4EKD7",
     "Miniature panel-mount momentary push button, **normally open**, black "
     "body and cap, threaded bushing with hex nut.\n\n"
     "**PBS-110-BK**, TWTADE brand. Amazon ASIN **X002B4EKD7**, sold as "
     "**12 pcs**. Original bag and spare nuts retained."),
    ("Panel-Mount Push Button, Assorted", "",
     "Mixed salvage lot of panel-mount push buttons - quality and vintage parts, "
     "not clones.\n\n"
     "Markings seen include **C&K 8168**. Bodies in maroon, mint-green, blue and "
     "black; caps in red and black; several with gold-plated terminals; sizes "
     "and bushing diameters vary. Both momentary and (probably) latching types "
     "are present - NOT sorted by action.\n\n"
     "**Read the part number off the body, and check the action with a meter, "
     "before specifying one.** This record answers 'do I have a panel button', "
     "nothing more.\n\n"
     "Worth revisiting if a project ever needs a specific one - there is real "
     "value in this tray and it is currently undifferentiated."),
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
