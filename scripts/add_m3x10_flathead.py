"""M3 x 10 flat head hex drive, stainless. Part record now, count when given.

Scott 2026-08-26: "M3x10 flat head hex drive" then "m3 is stainless".

NAMED FOR THE LABEL, NOT FOR THE VENDOR. "Flat Head Hex Screw, M3 x 10 mm" is
31 characters and prints on two lines with the length intact.

The part it sits next to shows why that matters. #980 is
"Black-Oxide Alloy Steel Hex Drive Flat Head Screw, 90 Degree Countersink,
M3 x 0.50 mm Thread, 30 mm Long" -- same thread, same head, same drive, 30 mm
instead of 10, and on 62 mm tape it truncates at "M3 x 0.50 mm…". The two would
be indistinguishable on the shelf.

They also differ in a way that matters more than length: #980 is BLACK-OXIDE
ALLOY STEEL and this is STAINLESS. Alloy steel is stronger and rusts; stainless
is weaker and does not. Reaching into the wrong bag is a real mistake, not a
cosmetic one.

Created without a stock row on purpose. The identity is fully determined and
the COUNT is not, and this repo's rule is that a quantity nobody counted is how
a stock system starts lying. The row goes in when Scott counts.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

NAME = "Flat Head Hex Screw, M3 x 10 mm"
DESC = ("Stainless steel flat head (countersunk) screw, hex socket drive, "
        "M3 x 0.5 thread, 10 mm long.")
NOTES = (
    "STAINLESS, stated by Scott 2026-08-26.\n\n"
    "NOT INTERCHANGEABLE WITH #980, which is the same thread, head and drive at "
    "30 mm long and is BLACK-OXIDE ALLOY STEEL. Alloy steel is stronger and "
    "rusts; stainless is weaker and does not. On tape #980's McMaster name "
    "truncates at 'M3 x 0.50 mm…', so the two are indistinguishable at the "
    "shelf unless the bags say so — which is why this one is named short and "
    "length-first.\n\n"
    "Arrived in an Amazon box, SKU X0003BBMNNL, label 'Flat Head Countersunk "
    "Mac…iture, DIY'. No order in this system matches that SKU and the Amazon "
    "order-history search did not surface it, so vendor and date are unknown "
    "and none is claimed.\n\n"
    "HOME: B1, the metric fastener cabinet, alongside the other M3s. Not the "
    "bearings bin it came off the shelf with.")

b1 = StockLocation.objects.get(name="B1")
print(f"name: {NAME} ({len(NAME)} chars)")
dup = Part.objects.filter(name=NAME).first()
print(f"duplicate: {dup.pk if dup else 'none'}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

p = dup or Part.objects.create(name=NAME, description=DESC, category_id=136,
                               default_location=b1, purchaseable=True, active=True)
Part.objects.filter(pk=p.pk).update(notes=NOTES, default_location=b1)
p.refresh_from_db()
print(f"\n[{p.pk}] {p.name}")
print(f"  default_location: {p.default_location.name}")
print(f"  stock rows: 0 — waiting on a count, deliberately")
