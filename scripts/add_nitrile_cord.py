"""uxcell nitrile round seal cord into Sealing & Weatherstrip.

Listing (Scott's order history, purchased 2025-07-17): uxcell Nitrile Rubber
Round Seal Strip, 3mm (1/8") diameter, 8 m / 26.25 ft, ASIN B0BHY918CR, 1 piece
per pack. Carton FNSKU X003FLIGWV, uxcell SKU S22101400ux0537.

Tracked in FEET to match #1146 in the same bin — both are continuous stock cut
in deliberate lengths for a job, which is the case where a running total stays
honest. The 8 m is recorded in the notes so the metric origin is not lost.

THE THREE ITEMS IN THIS BIN ARE NOT SUBSTITUTES and the notes say so, because
sharing a drawer is exactly what makes people assume they are.
"""
import argparse, datetime, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from company.models import Company, SupplierPart                 # noqa: E402
from part.models import Part                                     # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

BIN, QTY, ASIN, TODAY = "Sealing & Weatherstrip", 26.25, "B0BHY918CR", datetime.date.today()
NAME = "Nitrile Rubber Round Seal Cord, 3mm (1/8 in) dia, solid (uxcell)"
DESC = ("uxcell solid nitrile (NBR) round seal cord, 3 mm / 1/8 in diameter, "
        "supplied as one continuous 8 m (26.25 ft) length. Black. For DIY "
        "gaskets, industrial equipment and furniture.")
NOTES = (
 f"{QTY} FT ({8} m) — the pack figure for one continuous length, recorded "
 f"{TODAY}. Purchased 2025-07-17, $9.99.\n\n"
 "SOLID RUBBER, NOT FOAM — and this is the distinction that matters in a bin "
 "full of foam. The listing's own words: hard, low elasticity, does not go flat "
 "when pinched, difficult to stretch. It seals by filling a groove, not by "
 "squashing to close a gap. Put it where a foam strip belongs and it will hold "
 "the surfaces apart instead of sealing them.\n\n"
 "NITRILE IS AN OIL SEAL, NOT A WEATHER SEAL, whatever the listing title says. "
 "NBR is excellent against oil, fuel and hydraulic fluid — which is why it is "
 "the right cord for a machine cover or a gearbox lid. It is POOR against ozone "
 "and sunlight and will craze and crack outdoors over a season or two. For a "
 "door or window use the CR neoprene (#1146) instead; neoprene is the weather "
 "material and nitrile is the oil one.\n\n"
 "SO THE THREE ITEMS IN THIS BIN ARE NOT SUBSTITUTES:\n"
 "  #1146  CR neoprene foam cord, 3/8 x 1/4 in  — compressible, weatherproof,\n"
 "         takes a compression set. Door and window edges.\n"
 "  #1147  foam gasket strip, 34 x 7/8 in flat  — compressible, fixed pieces.\n"
 "  this   solid NBR round cord, 3 mm          — barely compressible, oil-\n"
 "         resistant, poor outdoors. Grooves and machine covers.\n"
 "Sharing a drawer is precisely what would make somebody assume otherwise.\n\n"
 "3 mm CORD WANTS A GROOVE ABOUT 2.4 mm DEEP to compress roughly 20 percent, "
 "which is the usual target for a static face seal. Squeeze a hard NBR cord much "
 "harder than that and it stops sealing better and starts distorting the joint.\n\n"
 f"Amazon ASIN {ASIN}; carton FNSKU X003FLIGWV, uxcell SKU S22101400ux0537. No "
 "purchase order in this system matches it.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.get(name=BIN)
if Part.objects.filter(name=NAME).exists():
    sys.exit("!! already exists")
cat = Part.objects.get(pk=1146).category
print(f"{NAME}\n  -> {loc.pathstring}, qty {QTY} ft, category {cat}")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

p = Part.objects.create(name=NAME, description=DESC, category=cat,
                        purchaseable=True, component=True, active=True)
Part.objects.filter(pk=p.pk).update(units="ft")
got = Part.objects.get(pk=p.pk).units
assert got == "ft", f"units did not stick: {got!r}"
from InvenTree.conversion import convert_physical_value          # noqa: E402
probe = float(convert_physical_value("8 m", got))
assert abs(probe - 26.2467) < 0.01, f"conversion broken: 8 m -> {probe} ft"
print(f"OK  units 'ft' verified — 8 m resolves to {probe:.4f} ft")

s = StockItem.objects.create(part=p, location=loc, quantity=QTY,
                             notes=f"{QTY} ft (8 m), one continuous length, pack "
                                   f"figure recorded {TODAY}.")
Part.objects.filter(pk=p.pk).update(notes=NOTES, default_location=loc)
amazon = Company.objects.get(name="Amazon", is_supplier=True)
if not SupplierPart.objects.filter(SKU=ASIN).exists():
    SupplierPart.objects.create(part=p, supplier=amazon, SKU=ASIN,
                                pack_quantity=str(QTY),
                                link=f"https://www.amazon.com/dp/{ASIN}")
f = StockItem.objects.get(pk=s.pk)
assert float(f.quantity) == QTY and f.location_id == loc.pk, "stock did not stick"
assert f.stocktake_date is None, "no stocktake date — nobody measured this"
print(f"OK  part #{p.pk}, stock #{f.pk} qty={float(f.quantity):g} ft in {loc.name}")
