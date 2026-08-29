"""Foam gasket strips, 34 x 7/8 in, 2 left, into Sealing & Weatherstrip.

Scott 2026-08-29: "34 in 7/8 foam gasket strips" ... "2 left amazon purch".

STOCKED IN STRIPS, NOT FEET, and that is a deliberate difference from #1146
sitting in the same bin. The Yotache weatherstrip is a continuous run you cut to
suit, so feet is the useful figure. These are FIXED 34 in pieces as purchased —
you reach for a strip, and a strip is what a job consumes. Two units in one bin
is fine when each matches how its product is actually used; forcing both to feet
would make "2 strips" read as 5.67 ft and mean nothing to anyone.

THICKNESS IS NOT RECORDED because it was not measured. For a gasket that is the
dimension that decides whether it works — length and width say where it fits,
thickness says how much gap it closes and how far it can compress. Left blank
and flagged rather than guessed from a photograph.

    itq run scripts/add_foam_gasket_strips.py            # dry run
    itq run scripts/add_foam_gasket_strips.py --commit
"""
import argparse, datetime, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory                       # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

BIN, QTY, TODAY = "Sealing & Weatherstrip", 2, datetime.date.today()
NAME = "Foam Gasket Strip, 34 x 7/8 in, adhesive-backed"
DESC = ("Flat black foam gasket strip, adhesive-backed, cut to 34 in long by "
        "7/8 in wide as purchased. Thickness not yet measured.")
NOTES = (
 f"COUNTED {TODAY}: 2 left. Scott — an Amazon purchase, so more were bought and "
 "some have been used; only what remains is recorded here.\n\n"
 "THICKNESS UNMEASURED, and for a gasket that is the dimension that matters. "
 "Length and width say where it fits; THICKNESS says how much gap it closes and "
 "how far it can compress. A caliper reading would complete this record. Not "
 "guessed from a photograph.\n\n"
 "STOCKED IN STRIPS, NOT FEET — deliberately different from the Yotache "
 "weatherstrip (#1146) in this same bin. That one is a continuous run you cut to "
 "suit, so feet is the useful figure. These are fixed 34 in pieces as purchased: "
 "you reach for a strip and a strip is what a job consumes. Two units in one bin "
 "is correct when each matches how its product is actually used. Forcing both to "
 "feet would render these as 5.67 ft, which means nothing to anyone.\n\n"
 "NOT INTERCHANGEABLE WITH #1146. That is 3/8 x 1/4 in CR neoprene cord for door "
 "and window edges; this is 7/8 in flat strip. They share a bin and a material "
 "family, not an application.\n\n"
 "Amazon purchase, ASIN unknown and no purchase order in this system matches it. "
 "Vendor is stated because Scott stated it; nothing more is claimed.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.get(name=BIN)
if Part.objects.filter(name=NAME).exists():
    sys.exit("!! already exists")
cat = Part.objects.get(pk=1146).category
print(f"{NAME}\n  -> {loc.pathstring}, qty {QTY} strips, category {cat}")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

p = Part.objects.create(name=NAME, description=DESC, category=cat,
                        purchaseable=True, component=True, active=True)
s = StockItem.objects.create(part=p, location=loc, quantity=QTY,
                             notes=f"COUNTED {TODAY}: 2 strips left.")
Part.objects.filter(pk=p.pk).update(notes=NOTES, default_location=loc)
StockItem.objects.filter(pk=s.pk).update(stocktake_date=TODAY)
f = StockItem.objects.get(pk=s.pk)
assert float(f.quantity) == QTY and f.stocktake_date == TODAY, "stock did not stick"
assert Part.objects.get(pk=p.pk).default_location_id == loc.pk, "home did not stick"
assert Part.objects.get(pk=p.pk).units in ("", None), \
    "units should stay unset — these are counted pieces, not a length"
print(f"\nOK  part #{p.pk}, stock #{f.pk} qty=2 strips in {loc.name}")
