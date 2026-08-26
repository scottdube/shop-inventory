"""Rename the Viton O-ring so its DASH NUMBER survives the label.

The label rendered as:

    Chemical-Resistant Viton Fluoroelastomer O-Ring, 3/32 Fractional Width, Da…

Three lines of adjectives and then a truncation exactly where the identity was.
Everything printed is true of hundreds of different O-rings; the one field that
says WHICH ONE -- Dash Number 135 -- fell off the end.

ROOT CAUSE: the McMaster import used the VENDOR DESCRIPTION as the part name.
Vendor descriptions are written to be searched, so they lead with material and
qualities and put the size last. A shelf label needs the reverse: the
discriminator first, because the reader is standing in front of six similar
bags trying to tell them apart.

This is not one bad name. Every McMaster-imported part is named this way, and
any of them whose distinguishing detail sits past ~40 characters will truncate
the same way. Checked here and recorded in TRAPS.

Full vendor description kept in `description`, where length costs nothing.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

NEW = "Viton O-Ring, Dash 135, 3/32 Width"
p = Part.objects.get(pk=1004)
print(f"{p.name!r}\n  -> {NEW!r}  ({len(NEW)} chars)")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

p.name = NEW
p.save()
Part.objects.filter(pk=1004).update(notes=(p.notes or "").rstrip() +
    "\n\nRENAMED 2026-08-26 for the label. The McMaster name — 'Chemical-"
    "Resistant Viton Fluoroelastomer O-Ring, 3/32 Fractional Width, Dash Number "
    "135' — truncated on 62 mm tape at 'Da…', dropping the dash number. "
    "Everything that printed was true of hundreds of O-rings; the field that "
    "said which one fell off the end.\n\n"
    "Vendor descriptions lead with material and qualities because they are "
    "written to be searched. A shelf label needs the discriminator first. Full "
    "vendor text is preserved in the description field.")
p.refresh_from_db()
print(f"renamed: {p.name}")

# how widespread is this? report only -- do not mass-rename unasked.
from stock.models import StockItem
print("\nOther McMaster-imported parts whose name exceeds 40 chars:")
n = 0
for q in Part.objects.filter(notes__icontains="McMaster-Carr").order_by("name"):
    if len(q.name) > 40:
        n += 1
        loc = StockItem.objects.filter(part=q).first()
        if n <= 12:
            print(f"  [{q.pk}] ({len(q.name)}) {q.name[:66]}")
print(f"  ... {n} in total")
