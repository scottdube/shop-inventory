"""B3-R1C6: two roller-lever microswitches, different sizes and ratings.

Kept separate because the size difference is the whole point: one is a 3D-printer
endstop / mouse-button class part, the other is a 5A SS-5GL2 form factor you
would actually switch a load with. Substituting one for the other fails either
mechanically or electrically.
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

NEW = [
    ("Microswitch Sub-Miniature Roller Lever 1A", "",
     "Sub-miniature snap-action microswitch with roller lever, SPDT (NO/NC/C).\n\n"
     "The small class - mouse-button / 3D-printer endstop size. Bodies marked "
     "**1A 125V AC** and **3A 125V AC** (the lot is mixed on rating; check the "
     "individual switch if it matters).\n\n"
     "Bag label (Chinese): `带柄滚轮鼠标开关` - roller-lever mouse switch.\n"
     "  batch 366707 · quantity **50** · D-6-21-2 · SF1637119076794 · 11/38\n\n"
     "NOT interchangeable with the SS-5GL2 in this same drawer - different size "
     "and an order of magnitude less current."),
    ("Taiss SS-5GL2 Roller Lever Microswitch 5A", "B07486RHH7",
     "Snap-action basic switch, simulated roller lever, SPDT, **5A**.\n\n"
     "**SS-5GL2** form factor (Omron's designation; Taiss is the brand here). "
     "Black body, red roller.\n\n"
     "Amazon ASIN **B07486RHH7**, sold as **10 pcs**. Original bag retained.\n\n"
     "The larger, load-rated switch of the two in this drawer."),
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
