import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

cat = (PartCategory.objects.filter(name="Electromechanical").first()
       or PartCategory.objects.filter(name="LEDs").first())

for size in ("3mm", "5mm"):
    name = f"LED Mounting Grommet {size}"
    if Part.objects.filter(name=name).exists():
        print(f"  exists          {name}")
        continue
    print(f"  CREATE          {name}")
    if a.commit:
        p = Part.objects.create(
            name=name, category=cat,
            description=f"Black rubber panel grommet for a {size} LED"[:250],
            notes=(f"Black rubber mounting grommet for a **{size}** LED - press "
                   "the LED in, then press the grommet into the panel hole.\n\n"
                   "Loose in B3-R2C3, **mixed in among the bulk LEDs rather than "
                   "separated**. Count is a rough eyeball, not a tally: Scott put "
                   "it at 15-20 each and the lower figure is recorded so the "
                   "number never overstates.\n\n"
                   "Worth bagging separately next time this drawer is open - "
                   "they are hard to see among the LED bodies."),
            active=True, component=True, purchaseable=True)
        print(f"          -> #{p.pk}")

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
