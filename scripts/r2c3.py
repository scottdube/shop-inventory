"""B3-R2C3: bulk 5mm LEDs, CLEAR/tinted lens.

Kept distinct from the diffused 5mm parts in R2C1: clear is a narrow bright
point, diffused is wide and soft. You choose between them on purpose, so they
are different parts.
"""
import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

cat = PartCategory.objects.filter(name="LEDs").first()
NOTE = ("5mm through-hole LED, **clear/tinted {c} lens** (not diffused).\n\n"
        "Bulk loose stock, no packaging - forward voltage and brightness "
        "unknown. Fine as an indicator; measure before designing around one.\n\n"
        "Distinct from the diffused 5mm parts in B3-R2C1: clear gives a narrow "
        "bright point, diffused a wide soft glow.")

for colour in ("Green", "Amber", "Red"):
    name = f"LED 5mm {colour} Clear"
    if Part.objects.filter(name=name).exists():
        print(f"  exists          {name}")
        continue
    print(f"  CREATE          {name}")
    if a.commit:
        p = Part.objects.create(
            name=name, category=cat,
            description=f"5mm through-hole LED, clear/tinted {colour.lower()} lens, bulk"[:250],
            notes=NOTE.format(c=colour.lower()),
            active=True, component=True, purchaseable=True)
        print(f"          -> #{p.pk}")

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
