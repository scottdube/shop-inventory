"""Identify three spring items from the bench photo. Specs now, locations later.

Scott 2026-08-26, answering three questions: "1 wb jones / 2 978 / 3 same".

ITEM 2 -> #978, confirmed. Bag is Associated Spring Raymond, MH0500.0759.00M,
"2 PER BAG", made in China, and the visible spring has an OPEN HOOK end. #978 is
the hook-end 5" extension spring; its sibling #977 is loop ends at 4.5". The bag
carries the MAKER's name, not McMaster's -- the same thing the Viton O-rings did
this afternoon, and the same lesson: packaging style is not evidence of vendor.

ITEM 3 -> #1132, same card, its reverse. The yellow face says "SPRINGS P-9602 /
QTY 2" and nothing else; the white back carries the dimensions that face was
missing. Recorded here, because "no dimensions anywhere" was written on this
part two hours ago and it is now false.

ITEM 1 -> #976 by ELIMINATION, not by reading. Scott says the maker is W.B.
Jones; the yellow "Line 3 on your packing list" sticker is McMaster's, so
McMaster resold it. Three McMaster compression-spring rows exist and two are
ruled out by the photograph:

  #1001  302 STAINLESS, 1" long, 5   -- ruled out: the springs are zinc-bright
  #1002  0.938" long, 0.188" OD, 12  -- ruled out: far too small for the bag
  #976   3" long, 0.5" OD, 6         -- fits what is visible

That is an inference from material and size, and it is written into the part as
an inference. NO COUNT IS SET from it: the quantity stays as the import left it
until somebody counts the bag.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

NOTES = {
1132: ("\n\nDIMENSIONS FOUND 2026-08-26 on the REVERSE of the card, which is "
       "white where the face is yellow: **15/32 in x 4-1/2 in x .041 in wire** "
       "(12 mm x 11.4 cm x 1 mm), **maximum safe load 5.28 lb / 2.4 kg**. "
       "Marked for lawnmower and automotive use.\n\n"
       "This part previously said 'NO DIMENSIONS ANYWHERE — the card gives a "
       "part number and a quantity and nothing else'. That was true of the FACE "
       "of the card and false of the card. Turn the packaging over before "
       "recording an absence.\n\n"
       "Also confirms the read taken off the first photograph: these are "
       "EXTENSION springs, and now by the maker's own word rather than by "
       "looking at the ends."),
978:  ("\n\nBAG IDENTIFIED 2026-08-26, confirmed by Scott. Associated Spring "
       "Raymond, MH0500.0759.00M, 'Description: 2 PER BAG', Cust RA703-DG09, "
       "country of origin CN. The visible spring has an OPEN HOOK end, which is "
       "what separates this from #977 (loop ends, 4-1/2 in).\n\n"
       "THE BAG CARRIES THE MAKER'S NAME, NOT MCMASTER'S. Same as the Viton "
       "O-rings the same afternoon: McMaster resells manufacturer-packed goods, "
       "so an unbranded bag is not evidence the part came from elsewhere.\n\n"
       "The '11094' on the label is a PRODUCTION quantity, not a bag count. Two "
       "per bag."),
976:  ("\n\nIDENTIFIED BY ELIMINATION 2026-08-26 — an inference, not a reading. "
       "Scott named the maker as **W.B. Jones**, and the bag carries McMaster's "
       "yellow 'Line 3 on your packing list' sticker, so McMaster resold it.\n\n"
       "Three McMaster compression-spring rows exist. Two are ruled out by the "
       "photograph:\n"
       "  #1001 is 302 STAINLESS and these are zinc-bright\n"
       "  #1002 is 0.938 in long, 0.188 in OD — far too small for what is in the bag\n"
       "leaving this one, 3 in long and 0.5 in OD.\n\n"
       "NO COUNT TAKEN FROM THAT. The quantity is still whatever the import "
       "recorded; identifying a bag is not counting it, and the bags on this "
       "bench have been wrong twice today already."),
}

for pk in NOTES:
    p = Part.objects.get(pk=pk)
    print(f"[{pk}] {p.name[:64]}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

for pk, add in NOTES.items():
    p = Part.objects.get(pk=pk)
    if "2026-08-26" not in (p.notes or "").split("SPRING HOME DECLARED")[-1][:200] or True:
        if add.strip()[:40] not in (p.notes or ""):
            Part.objects.filter(pk=pk).update(notes=(p.notes or "").rstrip() + add)
            print(f"  annotated [{pk}]")

# the card now has real dimensions -- put them in the description too
Part.objects.filter(pk=1132).update(
    description="Extension spring, 15/32 in OD x 4-1/2 in long x .041 in wire, "
                "max safe load 5.28 lb. Two per card, 'Hand Made Springs' P-9602.")
print("\ndone")
