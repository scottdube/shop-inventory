"""New container on WS2-S4 for sealing and weatherstrip stock, plus the foam tape.

Scott 2026-08-29: "we need a new container for the wires2 shelf 4, there will
be more."

WHY IT IS NOT 'Adhesives'. That bin (#586) holds things that BOND — solvent
cements, contact adhesive, gasket maker, activator. This foam tape is adhesive-
BACKED but its job is to seal and cushion, and a run of weatherstrip is bulky in
a way a tube of cement is not. Sorting by what a thing DOES keeps the adhesives
bin about adhesion; sorting by "it is sticky" would eventually put door seal,
gasket sheet and foam tape into the glue box.

Named for the category rather than the product, because Scott says more is
coming and a bin named for its first occupant is how the second one ends up
somewhere else -- the same mistake B3-R5C1 made calling itself 'ROUND'.

    itq run scripts/add_sealing_bin.py            # dry run
    itq run scripts/add_sealing_bin.py --commit
"""
import argparse, datetime, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from company.models import Company, SupplierPart                 # noqa: E402
from part.models import Part, PartCategory                       # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

SHELF, NAME, TODAY = 456, "Sealing & Weatherstrip", datetime.date.today()
LOCDESC = (
 "SEALING & WEATHERSTRIP. Foam tape, door and window seal, gasket stock, "
 "O-ring cord and anything whose job is to close a gap. Established 2026-08-29; "
 "Scott: \"there will be more.\"\n\n"
 "NOT the Adhesives bin next door (#586). That one holds things that BOND — "
 "solvent cements, contact adhesive, gasket maker. Weatherstrip is adhesive-"
 "BACKED but its job is to seal and cushion, and it is bulky in a way a tube is "
 "not. Sorting by what a thing does keeps both bins meaningful; sorting by "
 "\"it is sticky\" would put door seal in the glue box.\n\n"
 "Named for the category, not the first product in it.")

ASIN = "X002CFDGIF"
PNAME = "Foam Tape, CR neoprene weatherstrip, 2 strips x 33 ft (Yotache)"
PDESC = ("Yotache self-adhesive CR foam neoprene weatherstrip for doors and "
         "windows. Supplied as 2 strips of 33 ft each, black foam on a yellow "
         "release liner.")
PNOTES = (
 f"COUNTED {TODAY}: two strips, the full pack, unopened.\n\n"
 "CR NEOPRENE, NOT EPDM OR PVC — and the difference decides where it works. "
 "Neoprene shrugs off oil, ozone and weather, which suits a shop door. But it "
 "takes a COMPRESSION SET: squash it hard and it stays squashed, so it is a poor "
 "choice anywhere that clamps down and has to keep sealing after. EPDM recovers "
 "better under sustained compression; reach for that instead on a lid or a "
 "hatch that gets latched shut.\n\n"
 "ADHESIVE-BACKED, SO SURFACE PREP IS THE WHOLE JOB. It sticks to clean, dry, "
 "above about 10 C. Cold or dusty and it lets go weeks later, which reads as bad "
 "tape rather than bad prep.\n\n"
 "Pack is 2 STRIPS of 33 ft, 66 ft total. Stocked in STRIPS: a strip is what you "
 "reach for, and cutting one to length does not make the other half disappear. "
 "pack_quantity is 2 so the price divides per strip rather than booking the "
 "whole pack against one.\n\n"
 f"Amazon ASIN {ASIN}, brand Yotache. No purchase order in this system matches "
 "it — another purchase visible only because the box turned up.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

shelf = StockLocation.objects.get(pk=SHELF)
print(f"parent {shelf.pathstring}")
for l in StockLocation.objects.filter(parent=shelf).order_by("name"):
    print(f"  existing: {l.name}")
if StockLocation.objects.filter(name=NAME, parent=shelf).exists():
    sys.exit("!! that container already exists")
print(f"  NEW: {NAME}\n  then file: {PNAME[:60]}")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

loc = StockLocation.objects.create(name=NAME, parent=shelf, description=LOCDESC)
got = StockLocation.objects.get(pk=loc.pk)
assert got.parent_id == SHELF and "SEALING" in got.description, "location did not stick"
print(f"OK  location #{loc.pk} {got.pathstring}")

cat = (PartCategory.objects.filter(name__iexact="Hardware").first()
       or PartCategory.objects.filter(name__icontains="consumable").first())
p = Part.objects.create(name=PNAME, description=PDESC, category=cat,
                        purchaseable=True, component=True, active=True)
s = StockItem.objects.create(part=p, location=loc, quantity=2,
                             notes=f"COUNTED {TODAY}: 2 strips, unopened pack.")
Part.objects.filter(pk=p.pk).update(notes=PNOTES, default_location=loc)
StockItem.objects.filter(pk=s.pk).update(stocktake_date=TODAY)
amazon = Company.objects.get(name="Amazon", is_supplier=True)
if not SupplierPart.objects.filter(SKU=ASIN).exists():
    SupplierPart.objects.create(part=p, supplier=amazon, SKU=ASIN,
                                pack_quantity="2",
                                link=f"https://www.amazon.com/dp/{ASIN}")
f = StockItem.objects.get(pk=s.pk)
assert float(f.quantity) == 2 and f.stocktake_date == TODAY, "stock did not stick"
assert Part.objects.get(pk=p.pk).default_location_id == loc.pk, "home did not stick"
print(f"OK  part #{p.pk}, stock #{f.pk} qty=2 strips in {got.name}")
