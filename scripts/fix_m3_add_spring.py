"""M3 x 10 is 100, not 45. And the P-9602 spring card.

Scott 2026-08-26: "100 on the m3's, 2 springs 1 card".

THE 45 WAS MINE TO GET WRONG. Two counts were outstanding when he said
"count 45" -- the M3 screws and the spring cards -- and I picked the M3s
because 45 cards of springs made no sense. It went in with a note saying so.
It was neither: almost certainly the Kerr 1/4-20 box, which was the item under
discussion in the same breath.

The note that said "say so if that reading is wrong" is the only reason this
was cheap to fix. A bare number attached to the wrong part with no stated
assumption would have read as a count forever.

**A bare count needs its part named in the same message.** The dictation format
agreed earlier does this -- "608 ZZ count 13" -- and it broke down here because
the number arrived on its own while two questions were open. Ask which, or say
which you assumed.

SPRINGS: one card, two springs, "Hand Made Springs P-9602". No size on the
card. Counted in PIECES (2), not cards, because a card is packaging and this
repo counts pieces.

NO LOCATION SET FOR THE SPRING. Five McMaster spring rows are already unlocated
and there is no spring home in the shop; deciding one for this card alone would
be guessing at where all six should go.
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
si = StockItem.objects.get(pk=711)
print(f"M3 x 10: {si.quantity:g} -> 100")

SNAME = "Extension Spring, card P-9602"
SDESC = ("Small extension spring with loop ends, on a 'Hand Made Springs' "
         "retail card marked P-9602. Two per card. No dimensions printed.")
SNOTES = (
    "TWO SPRINGS ON ONE CARD, counted in PIECES not cards -- a card is "
    "packaging, and this shop counts pieces.\n\n"
    "NO DIMENSIONS ANYWHERE. The card gives a part number and a quantity and "
    "nothing else: no free length, OD, wire gauge or rate. Measure before "
    "designing anything around them, and write the numbers here when you do.\n\n"
    "Read as EXTENSION springs (loop ends, close-wound) off the photograph. "
    "That is an identification from a picture and has not been confirmed in "
    "hand.\n\n"
    "NOT the five McMaster spring rows (#976 #977 #978 #1001 #1002), which are "
    "a different purchase and are all still unlocated. This is a retail card.\n\n"
    "NO HOME CHOSEN. There is no spring location in this shop and six spring "
    "rows now want one. Picking a cell for this card alone would prejudge where "
    "the other five go.")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

si.add_stock(55, user, notes="Count corrected 45 -> 100 by Scott, 2026-08-26.")
si.refresh_from_db()
StockItem.objects.filter(pk=711).update(
    stocktake_date=datetime.date(2026, 8, 26),
    notes=("TALLIED 2026-08-26. Scott counted 100.\n\n"
           "CORRECTED from 45. That number arrived as a bare 'count 45' while "
           "TWO counts were outstanding -- these screws and the spring cards -- "
           "and it was assigned here on the reasoning that 45 spring cards is "
           "not a thing. It was neither; it appears to have been the Kerr "
           "1/4-20 box, which was under discussion in the same breath.\n\n"
           "The assumption was written into the row when it was made, which is "
           "the only reason it was cheap to undo. A bare number attached to the "
           "wrong part with no stated assumption reads as a count forever."))

p = Part.objects.filter(name=SNAME).first()
if not p:
    p = Part.objects.create(name=SNAME, description=SDESC, category_id=137,
                            purchaseable=True, active=True)
    print(f"spring part [{p.pk}] created")
Part.objects.filter(pk=p.pk).update(notes=SNOTES)
sp = StockItem.objects.filter(part=p).first()
if not sp:
    sp = StockItem.objects.create(part=p, location=None, quantity=2)
StockItem.objects.filter(pk=sp.pk).update(
    stocktake_date=datetime.date(2026, 8, 26),
    notes=("TALLIED 2026-08-26. Scott: two springs, one card.\n\n"
           "UNLOCATED ON PURPOSE, not by oversight: no spring home exists yet "
           "and five other spring rows are waiting on the same decision."))

si.refresh_from_db(); sp.refresh_from_db()
print(f"\nM3 x 10:  {si.quantity:g} @ {si.location.name} stocktake={si.stocktake_date}")
print(f"springs:  [{p.pk}] {sp.quantity:g} @ {sp.location or 'UNLOCATED (deliberate)'}")
