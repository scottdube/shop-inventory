"""Add the '10value 4x7mm Electrolytic Capacitors' bag, transcribed from its label.

Eight of its ten values already exist as Parts, created by explode_kits from
KIT15. Creating them again is exactly the duplicate mess the Amazon import
taught us to avoid, so this creates only the two genuinely new values and
cross-references the rest: one Part per value, listed in every kit that holds it.

NO QUANTITY IS RECORDED. The bag label is a value table only - it carries no
piece count - and inventing one is worse than leaving it blank. A bin check
sets the numbers.

Idempotent. Dry run unless --commit.
"""

import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockLocation  # noqa: E402

KIT = "Kit - 10-Value Electrolytic 4x7"
KIT_DESC = "10value 4x7mm Electrolytic Capacitors - bagged, NewAge cabinet"
CCAT = "Electronics/Passives/Capacitors"

# value, voltage - exactly as printed on the bag label, left column then right
KIT10 = [
    ("0.1uF", "50V"), ("1uF", "50V"), ("2.2uF", "50V"), ("3.3uF", "50V"),
    ("4.7uF", "50V"), ("10uF", "25V"), ("22uF", "16V"), ("22uF", "25V"),
    ("47uF", "10V"), ("100uF", "10V"),
]

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()


def category(path):
    parent = None
    for name in path.split("/"):
        if a.commit:
            parent, _ = PartCategory.objects.get_or_create(name=name, parent=parent)
        else:
            parent = PartCategory.objects.filter(name=name, parent=parent).first()
    return parent


kits_root = StockLocation.objects.filter(name="Kits").first()
if not kits_root:
    sys.exit("no 'Kits' location - run explode_kits.py first")

home = StockLocation.objects.filter(name=KIT, parent=kits_root).first()
if not home:
    print(f"kit location: CREATE  {KIT}")
    if a.commit:
        home = StockLocation.objects.create(name=KIT, parent=kits_root,
                                            description=KIT_DESC[:250])
else:
    print(f"kit location: exists  {KIT}")

created = crossref = 0
for val, volts in KIT10:
    name = f"Capacitor Electrolytic {val} {volts} (4x7)"
    p = Part.objects.filter(name=name).first()

    if p:
        tag = f"Also in: {KIT}."
        already = tag in (p.notes or "")
        print(f"  {name:<44} EXISTS  #{p.pk}"
              f"{'  (already cross-referenced)' if already else '  -> cross-reference'}")
        if not already:
            crossref += 1
            if a.commit:
                p.notes = ((p.notes or "").rstrip() + f"\n\n{tag}").strip()
                p.save()
        continue

    print(f"  {name:<44} NEW     -> {KIT}")
    created += 1
    if a.commit:
        note = (f"Aluminium electrolytic capacitor, {val} {volts}, 4x7mm body.\n\n"
                f"From the {KIT_DESC}. **Piece count unknown** - the bag label "
                "lists values only. Count at next bin check.")
        Part.objects.create(
            name=name[:100], description=note.split("\n")[0][:250],
            category=category(CCAT), default_location=home,
            active=True, component=True, purchaseable=True, notes=note,
        )

print(f"\n{'WROTE' if a.commit else 'DRY RUN - nothing written'}")
print(f"  new parts:        {created}")
print(f"  cross-referenced: {crossref}")
if not a.commit:
    print("\nre-run with --commit to apply")
