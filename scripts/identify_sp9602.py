"""P-9602 is Prime-Line SP 9602. Full dimensions at last, and they are not close.

Scott 2026-08-26 sent the Amazon listing, ASIN B008RFNRIW, last purchased
2024-01-14, $9.99:

  Prime-Line SP 9602 Extension Spring, Spring Steel Construction,
  NICKEL-PLATED Finish, 0.047 GA x 7/16 In. x 1-1/2 In., Closed Single Loop,
  (2 Pack)

  "Spring dimensions: 7/16 inch outside diameter, 1-1/2 inch length, 0.047 inch
   wire diameter, 11.5 lbs. maximum safe load, 1.71 inch maximum deflection"

The card's "P-9602" is Prime-Line's SP 9602. That is the whole mystery: a hang
card printed with a part number and no dimensions, from a maker whose own
listing carries all of them.

HOW FAR OFF THE EARLIER GUESS WAS. This part briefly carried 15/32 in x 4-1/2 in
x .041, borrowed from the white card in the same cell. Against the real figures:

                      SP 9602 (this)      white card (the 4-1/2 in lot)
  outside diameter    7/16  = 0.4375      15/32 = 0.4688
  free length         1-1/2 in            4-1/2 in
  wire                0.047 in            0.041 in
  finish              NICKEL-plated       zinc
  max safe load       11.5 lb             5.28 lb

**The ODs are within 1/32 of an inch and everything else is different.** The
lengths differ threefold and the load rating by more than double. Two springs
that would sit side by side in a drawer looking like variants of one product
are not remotely interchangeable, and the OD -- the dimension a person eyeballs
first -- is the one that matches.

NICKEL-PLATED, and the listing sells it as corrosion resistant for indoor and
outdoor use. That is a genuine difference from the zinc one, not marketing:
these are the pair to reach for anywhere damp.
"""
import argparse, os, sys, time, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.utils import OperationalError
from part.models import Part
from stock.models import StockItem

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

p = Part.objects.get(name="Extension Spring, card P-9602")
NEW = "Extension Spring, 7/16 x 1-1/2 in"
print(f"{p.name!r} -> {NEW!r} ({len(NEW)} chars)")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

def rename():
    p.name = NEW
    p.save()
retry(rename, "rename")

retry(lambda: Part.objects.filter(pk=p.pk).update(
    description="Extension spring, Prime-Line SP 9602. 7/16 in OD x 1-1/2 in "
                "long x 0.047 in wire, nickel-plated spring steel, closed single "
                "loop ends. Max safe load 11.5 lb, max deflection 1.71 in. Sold "
                "2 per card.",
    notes="**Prime-Line SP 9602.** The 'P-9602' on the yellow hang card is "
          "Prime-Line's part number. ASIN B008RFNRIW, last purchased "
          "2024-01-14, $9.99 for a 2-pack.\n\n"
          "7/16 in OD, 1-1/2 in free length, 0.047 in wire, NICKEL-PLATED "
          "spring steel, closed single loop both ends. **Max safe load 11.5 lb, "
          "max deflection 1.71 in.**\n\n"
          "**NOT the 4-1/2 in loop-end spring in this same cell, and the "
          "difference is bigger than it looks:**\n\n"
          "| | SP 9602 | the 4-1/2 in lot |\n"
          "|---|---|---|\n"
          "| OD | 7/16 (0.4375) | 15/32 (0.4688) |\n"
          "| free length | 1-1/2 in | 4-1/2 in |\n"
          "| wire | 0.047 | 0.041 |\n"
          "| finish | nickel | zinc |\n"
          "| max load | 11.5 lb | 5.28 lb |\n\n"
          "The ODs are within 1/32 in and everything else differs — length "
          "threefold, load rating more than double. The dimension a person "
          "eyeballs first is the one that matches, which is what makes them easy "
          "to confuse in a drawer.\n\n"
          "NICKEL-PLATED and sold as corrosion resistant indoors and out. That "
          "is a real difference from the zinc-plated 4-1/2 in springs: these are "
          "the pair to reach for anywhere damp.\n\n"
          "This part briefly carried the 4-1/2 in card's dimensions, merged in "
          "error on 2026-08-26 and corrected the same day."), "notes")

si = StockItem.objects.filter(part=p).first()
retry(lambda: StockItem.objects.filter(pk=si.pk).update(
    notes=(si.notes or "").rstrip() +
    "\n\nIDENTIFIED 2026-08-26 as Prime-Line SP 9602 from the Amazon listing "
    "Scott sent. Dimensions are no longer unknown: 7/16 in OD x 1-1/2 in x "
    "0.047 in wire, nickel, 11.5 lb max safe load.\n\n"
    "The 2 on the shelf is a 2-pack's worth and matches the card — but it is a "
    "COUNT, taken 2026-08-26, not the pack figure trusted."), "stock note")

p.refresh_from_db(); si.refresh_from_db()
print(f"\n{p.name}")
print(f"  {p.description}")
print(f"  {si.quantity:g} @ {si.location.name}, stocktake {si.stocktake_date}")
