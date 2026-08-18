import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

cat = (PartCategory.objects.filter(name="Electromechanical").first()
       or Part.objects.get(pk=98).category)

name = "AA Battery Spring Plate Contact"
note = ("Spring plate battery contacts for AA cells - the sprung negative "
        "terminal that goes in a battery compartment.\n\n"
        "**Package unopened** as of 2026-08-17, so no manufacturer or part "
        "number was read. Named from Scott's own drawer label. If the "
        "packaging is opened later, photograph the label — supplier and pack "
        "size are recoverable then and not before.")

p = Part.objects.filter(name=name).first()
if p:
    print(f"  exists  #{p.pk}  {name}")
else:
    print(f"  CREATE          {name}   (category {cat.pathstring})")
    if a.commit:
        p = Part.objects.create(
            name=name, category=cat,
            description="Sprung negative battery terminal for AA cells"[:250],
            notes=note, active=True, component=True, purchaseable=True)
        print(f"          -> #{p.pk}")
print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
