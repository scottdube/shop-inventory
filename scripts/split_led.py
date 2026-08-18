"""Split the assorted LED bag by colour - colour IS the selection criterion.

Same reasoning as momentary vs maintained on the toggles: if the user reaches
for it BY that attribute, the attribute belongs in the record, not in a note.
"""
import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

base = Part.objects.get(pk=756)
NOTE = ("5mm through-hole LED, diffused lens, {c}.\n\n"
        "From a loose mixed bag in B3-R2C1 - no packaging, so forward voltage "
        "and brightness are unknown. Fine for indicators; measure before "
        "designing around one.")

print(f"  rename #756 -> LED 5mm Red Diffused")
if a.commit:
    base.name = "LED 5mm Red Diffused"
    base.description = "5mm through-hole LED, diffused red lens, loose bag stock"[:250]
    base.notes = NOTE.format(c="**red**")
    base.save()

for colour in ("Green", "Blue"):
    name = f"LED 5mm {colour} Diffused"
    if Part.objects.filter(name=name).exists():
        print(f"  exists          {name}")
        continue
    print(f"  CREATE          {name}")
    if a.commit:
        p = Part.objects.create(
            name=name, category=base.category,
            description=f"5mm through-hole LED, diffused {colour.lower()} lens, loose bag stock"[:250],
            notes=NOTE.format(c=f"**{colour.lower()}**"),
            active=True, component=True, purchaseable=True)
        print(f"          -> #{p.pk}")

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
