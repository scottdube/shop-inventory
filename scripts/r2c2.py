import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

cat = PartCategory.objects.filter(name="LEDs").first()

NEW = [
    ("LED 2x5x7mm White Diffused Rectangular", "",
     "Rectangular flat-top LED, **2 x 5 x 7 mm**, white diffused lens, "
     "through-hole.\n\n"
     "Bag label: `100pcs 2x5x7mm White diffused`.\n\n"
     "**Bought specifically for the flight simulator build** - used in the "
     "**audio panels**. The rectangular body is the point: it suits a panel "
     "legend/annunciator window, which a round 5mm will not. Do not substitute "
     "a round LED here."),
    ("Adafruit LED Sequins - Emerald Green", "P1756",
     "**Adafruit LED Sequins**, emerald green, sewable/solderable PCB LED "
     "modules.\n\n"
     "Adafruit PID **1756** - http://adafru.it/1756. Sold as a **5 pack**. "
     "Bag code C8585-002."),
]

for name, ipn, note in NEW:
    p = Part.objects.filter(name=name).first()
    if p:
        print(f"  exists  #{p.pk}  {name}")
        continue
    print(f"  CREATE          {name}")
    if a.commit:
        p = Part.objects.create(
            name=name[:100], IPN=ipn, category=cat,
            description=note.split("\n")[0].replace("**", "")[:250], notes=note,
            active=True, component=True, purchaseable=True)
        print(f"          -> #{p.pk}")

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
