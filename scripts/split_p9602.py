"""Split two spring products I had merged into one part.

Scott 2026-08-26: "the p9602 card is two springs and they are not 4.5\", there
was a lot of 3 springs that are 4.5\" but they are not p9602".

WHAT WENT WRONG. Two cards were photographed hours apart:

  - a YELLOW hang card, "Hand Made Springs", "P-9602", "QTY 2"
  - a WHITE card, "EXTENSION SPRING / 15/32" x 4-1/2" x .041 / max safe load
    5.28 lbs"

I asked whether the white one was the back of the yellow one. Scott answered
"same" -- meaning the same card he had already shown me -- and I read it as
"same card, both faces". They are different products.

So one part ended up carrying the P-9602 name, the white card's dimensions, and
a quantity of 3 that came from the 4-1/2 in lot. Three facts about two things.

THE ASK THAT WOULD HAVE CAUGHT IT was badly built: "same card as the yellow
P-9602 one, or a second card?" offers "same" as a one-word answer to a question
about identity, and "same" is exactly what a person says about a thing they have
already shown you. **Do not offer a bare yes/no for an identity question --
ask which of the two it is, so the answer has to name one.**

The split:
  THIS PART  -> the 4-1/2 in lot. Keeps the dimensions, keeps quantity 3, keeps
                its place in the springs cell, LOSES the P-9602 name.
  NEW PART   -> the actual P-9602 card. Two springs, dimensions UNKNOWN, and
                explicitly NOT 4-1/2 in. Unlocated: whether that card was among
                the three handled on the bench has not been established, and
                assuming it was is the mistake retracted twenty minutes ago.
"""
import argparse, os, sys, time, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.utils import OperationalError
from part.models import Part
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

def retry(fn, what, tries=6):
    for i in range(tries):
        try:
            return fn()
        except OperationalError as e:
            if "locked" not in str(e).lower() or i == tries - 1:
                raise
            print(f"  locked on {what}, retry {i+1}")
            time.sleep(0.5 * (2 ** i))

cell = StockLocation.objects.get(pk=289)
p = Part.objects.get(pk=1132)
si = StockItem.objects.filter(part=p).first()
NEW = "Extension Spring, 4-1/2 in, loop ends"
print(f"existing: {p.name!r}  qty={si.quantity:g} @ {si.location.name if si.location else '-'}")
print(f"  -> {NEW!r}  ({len(NEW)} chars)")
print(f"new part: the actual P-9602 card, 2 springs, size unknown")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

def rename():
    p.name = NEW
    p.save()
retry(rename, "rename")

retry(lambda: Part.objects.filter(pk=1132).update(
    description="Extension spring, LOOP ends, 15/32 in OD x 4-1/2 in long x "
                ".041 in wire, zinc, max safe load 5.28 lb. Retail card stock.",
    notes="**Extension spring, 4-1/2 in, loop ends.** 15/32 in OD x .041 in "
          "wire, zinc-plated, max safe load 5.28 lb / 2.4 kg. Card marks it for "
          "lawnmower and automotive use.\n\n"
          "**NOT P-9602.** This part carried that name until 2026-08-26 because "
          "two different cards were photographed hours apart and I merged them: "
          "a yellow 'Hand Made Springs P-9602, QTY 2' hang card, and this white "
          "'EXTENSION SPRING' card with the dimensions on it. Scott: \"the p9602 "
          "card is two springs and they are not 4.5in, there was a lot of 3 "
          "springs that are 4.5in but they are not p9602.\" The P-9602 card is "
          "now its own part.\n\n"
          "RETAIL GRADE, NOT MUSIC WIRE. The McMaster music-wire loop-end spring "
          "at 4-1/2 in x 1/2 in OD is a near-twin — 1/32 in apart on OD, same "
          "length, same ends — and is CONSUMED, fitted to the sim rudder pedals. "
          "A call for it will come looking here. Zinc-plated low-carbon takes a "
          "permanent set under sustained load where music wire holds its rate, "
          "so this is fine for light intermittent work and wrong for anything "
          "that has to stay sprung.\n\n"
          "Card metric figures check against the imperial: 15/32 in = 11.9 mm "
          "(card says 12), 4-1/2 in = 11.43 cm (11.4), .041 in = 1.04 mm (1)."),
    "notes")

retry(lambda: StockItem.objects.filter(pk=si.pk).update(
    notes="TALLIED 2026-08-26. Scott counted 3.\n\n"
          "Three springs, and they are a LOT rather than a card of a fixed "
          "count — the '+1 found on the bench' that took this from 2 to 3 "
          "belongs here, not to the P-9602 card.\n\n"
          "Located in the springs cell: this was one of the three spring items "
          "physically on the bench and handled."), "stock note")

NAME2 = "Extension Spring, card P-9602"
q = Part.objects.filter(name=NAME2).first()
if not q:
    q = retry(lambda: Part.objects.create(
        name=NAME2, category_id=137, purchaseable=True, active=True,
        description="Extension spring on a yellow 'Hand Made Springs' hang card, "
                    "P-9602, two per card. Dimensions not recorded — NOT 4-1/2 in."),
        "create")
    print(f"  created the P-9602 part")
retry(lambda: Part.objects.filter(pk=q.pk).update(default_location=cell,
    notes="**Yellow 'Hand Made Springs' hang card, marked P-9602, QTY 2.**\n\n"
          "DIMENSIONS UNKNOWN and deliberately blank. The 15/32 in x 4-1/2 in x "
          ".041 figures that were briefly attached to this name belong to a "
          "DIFFERENT card — a white 'EXTENSION SPRING' card, now its own part. "
          "Scott: \"the p9602 card is two springs and they are not 4.5in.\"\n\n"
          "So the one thing known about the size is what it is NOT. Measure the "
          "springs and record free length, OD and wire before using them for "
          "anything.\n\n"
          "UNLOCATED. Whether this card was among the three spring items handled "
          "on the bench has not been established, and assuming it was is the "
          "error retracted for two other spring rows the same afternoon."),
    "notes2")

r = StockItem.objects.filter(part=q).first()
if not r:
    r = retry(lambda: StockItem.objects.create(part=q, location=None, quantity=2), "stock2")
retry(lambda: StockItem.objects.filter(pk=r.pk).update(
    notes="Two per the card. NOT a count — nobody has counted this card since "
          "it was photographed, and no stocktake_date is set.\n\n"
          "UNLOCATED on purpose: it has not been confirmed on a shelf."), "note2")

si.refresh_from_db(); p.refresh_from_db(); r.refresh_from_db(); q.refresh_from_db()
print(f"\n  {p.name}: {si.quantity:g} @ {si.location.name}")
print(f"  {q.name}: {r.quantity:g} @ {r.location.name if r.location else 'UNLOCATED'}")
print(f"springs cell holds {StockItem.objects.filter(location=cell).count()} rows")
