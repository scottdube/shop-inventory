import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

cat = PartCategory.objects.filter(name="LEDs").first() or Part.objects.get(pk=98).category
print(f"category: {cat.pathstring}")

NEW = [
    ("LED 5mm Assorted Red/Green/Blue", "",
     "Loose bag of 5mm through-hole LEDs, diffused, mixed **red / green / blue**.\n\n"
     "Not sorted by colour - if a count per colour is ever needed, that is a "
     "separate job."),
    ("B4304H1 Red LED 5mm (25-pack card)", "B4304H1",
     "5mm red LED, diffused red lens, on the original retail card.\n\n"
     "Card reads **B4304H1 - 25 PACK RED LED**, `...se Electronics Inc.` "
     "(maker name torn), Plainview, N.Y. 11803. UPC 76137-00283.\n\n"
     "The card's instruction sheet covers series **3900 / 4300 / 4400 / 5100** "
     "(CMD2040WC, CMD333UWC) and carries dropping-resistor tables for 6V/12V/28V "
     "AC and DC, polarity identification, and panel-clip drill sizes (17/64\" for "
     "the 4304 series, .265\" punch for 4305 CH).\n\n"
     "Vintage US retail stock - keep the card, it is the only documentation."),
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
