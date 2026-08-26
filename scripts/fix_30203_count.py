"""Correct the 30203 to FIVE pieces. The "2 Sets" reading was wrong.

Scott counted five boxes and went and read the listing. He is right.

WHAT I GOT WRONG AND HOW. The order-history SEARCH RESULT shows a truncated
title -- "2 Sets 30203 Tapered Roller Bearing 17x40x12mm" -- and the order
details page shows one line at $19.99 with no quantity multiplier. From those
two I concluded one unit of a two-set listing, i.e. 2 sets, and said so.

The actual listing (ASIN B077KFZL1K, brand KOB) is titled:

    "30203 Tapered Roller Ball Bearing 17x40x12mm 2-Sets of Metal Bearings
     - 5 pcs"

and its About-this-item bullet reads "INCLUDES: 5 pc - 30203 Tapered Roller
Ball Bearing". FIVE. The title contradicts itself -- "2-Sets" and "5 pcs" in
one line -- and the order page had truncated away the half that was right.

The lesson is not "read more carefully". It is that ORDER HISTORY IS A
TRUNCATED VIEW OF A LISTING, and a quantity taken from it is second-hand. Two
independent sources now agree on five: the listing's own contents bullet, and
Scott counting five boxes on the bench. The count that settles it is the one
from the bench.

So: 5 pieces, each an individual boxed tapered roller bearing (cone and cup
matched as one bearing), NOT 2 two-piece sets.
"""
import argparse, os, sys, django, datetime

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from part.models import Part
from stock.models import StockItem

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
p = Part.objects.get(pk=1124)
si = StockItem.objects.filter(part=p).first()
print(f"[{p.pk}] {p.name}\n  stock[{si.pk}] qty={si.quantity:g} stocktake={si.stocktake_date}")

NEWNAME = "Tapered Roller Bearing 30203, 17 x 40 x 12 mm"
NOTES = (
    "BORE 17.000 mm · OD 40.000 mm · WIDTH 13.250 mm\n\n"
    "FIVE individual bearings, each boxed. Each one is a matched cone (inner "
    "ring + rollers) and cup (outer race) -- that pairing is what the seller's "
    "title calls a 'set'. Cone and cup are lapped together and must never be "
    "mixed between bearings: a swapped pair assembles perfectly and is scrap.\n\n"
    "COUNT CORRECTED 2026-08-26 from 2 to 5. It had been entered as '2 Sets' "
    "off the bag label and the order-history search result, both of which show "
    "a TRUNCATED listing title. The full listing (ASIN B077KFZL1K, brand KOB) "
    "is titled '...2-Sets of Metal Bearings - 5 pcs' and its contents bullet "
    "says 'INCLUDES: 5 pc'. The title contradicts itself; the bench does not. "
    "Scott counted five boxes.\n\n"
    "WIDTH: the label says 17x40x12mm. 12 mm is the cone width B; the 30203 "
    "standard OVERALL width T is 13.25 mm, and T is what a housing gets cut "
    "for. Neither is measured.\n\n"
    "NOT A DROP-IN FOR THE 6203-2RS (#1121), WHICH IS ALSO 17 x 40 x 12. Same "
    "bore, same OD, same nominal width, different bearing entirely:\n"
    "  - Tapered rollers carry combined radial + THRUST load, in ONE direction, "
    "and are normally fitted in opposed pairs.\n"
    "  - They must be PRELOADED or set with endplay on assembly. A deep-groove "
    "ball bearing is pressed in and forgotten.\n"
    "  - Run one unpreloaded, or singly where thrust reverses, and it fails.\n"
    "This is the most dangerous pair in the bin precisely because the envelope "
    "matches: it will go in where the 6203 goes.\n\n"
    "PURCHASED: Amazon order 111-9180031-3026635, 2022-12-11, seller "
    "Dr.Bearing, $19.99, paid from gift card balance. One unit of the listing, "
    "which contains five. Listing is now marked Currently Unavailable.")

if not a.commit:
    print(f"\nwould set 5 and rename to {NEWNAME}\nDRY RUN -- add --commit")
    sys.exit()

if p.name != NEWNAME:
    p.name = NEWNAME
    p.save()
Part.objects.filter(pk=1124).update(notes=NOTES)

si.add_stock(3, user, notes="Count corrected 2 -> 5: Scott counted five boxes, "
                            "and the listing says 5 pcs. 2026-08-26.")
si.refresh_from_db()
StockItem.objects.filter(pk=si.pk).update(
    stocktake_date=datetime.date(2026, 8, 26),
    notes=("TALLIED 2026-08-26. Scott counted FIVE boxes on the bench, one "
           "bearing per box.\n\n"
           "Was 2, entered from the bag label's '2 Sets' and never counted. The "
           "listing's own contents bullet says 5 pcs; the label and the "
           "order-history title are both truncated forms of a "
           "self-contradictory seller title. The bench count and the listing "
           "agree, so this is a real count and not a pack figure."))

si.refresh_from_db(); p.refresh_from_db()
print(f"\n[{p.pk}] {p.name}")
print(f"  stock[{si.pk}] qty={si.quantity:g} stocktake={si.stocktake_date}")
