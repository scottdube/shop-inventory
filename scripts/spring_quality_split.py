"""#1132 and #977 are near-identical on paper and are not the same spring.

Scott 2026-08-26, looking at the P-9602 card: "I don't think these are nine
seventy seven. I think these are from somewhere else. These are low quality
springs. They don't look like my McMaster. These look like, uh, Amazon."

THE SPECS ARE 1/32 OF AN INCH APART:

  #1132  P-9602 retail card   15/32" OD  x 4-1/2" long  x .041" wire, zinc
  #977   McMaster 9432K...    1/2"   OD  x 4-1/2" long, MUSIC WIRE

Same length, same loop ends, ODs that differ by 0.031". On a shelf, in a bag,
they are the same spring. They are not.

MUSIC WIRE IS THE WHOLE DIFFERENCE. ASTM A228 music wire is high-carbon,
cold-drawn, and holds its rate; a zinc-plated low-carbon retail spring takes a
permanent set under sustained load and comes back shorter than it went in.
Swapping one for the other is a slow failure, not an obvious one -- the
mechanism works and then quietly stops returning.

Scott identified it BY EYE, from finish and feel, before any number was
compared. That is worth recording as evidence in its own right: the person who
bought both can tell them apart across a bench, and the catalogue could not.

#977 REMAINS UNSEEN. It has not turned up on the bench, is still unlocated, and
must not be quietly satisfied by the card that looks like it.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

A = ("\n\n**NOT #977, AND THE SPECS ARE 1/32 IN APART.** Scott, 2026-08-26: "
     "\"I don't think these are nine seventy seven... these are low quality "
     "springs. They don't look like my McMaster. These look like Amazon.\"\n\n"
     "#977 is McMaster MUSIC WIRE, 1/2 in OD x 4-1/2 in, loop ends. This card "
     "is 15/32 in OD x 4-1/2 in, zinc-plated, retail. Same length, same end "
     "type, ODs 0.031 in apart — indistinguishable in a bag.\n\n"
     "MUSIC WIRE IS THE DIFFERENCE THAT MATTERS. ASTM A228 is high-carbon and "
     "holds its rate; a zinc-plated low-carbon retail spring takes a permanent "
     "set under sustained load and comes back shorter than it went in. "
     "Substituting one for the other fails slowly — the mechanism works, then "
     "quietly stops returning.\n\n"
     "Use this one where the load is light and intermittent. Reach for #977 "
     "where something has to stay sprung.\n\n"
     "Scott called it by eye from finish and feel, before any dimension was "
     "compared. The catalogue could not have.")

B = ("\n\n**A RETAIL NEAR-TWIN EXISTS: #1132**, the P-9602 card. 15/32 in OD "
     "against this part's 1/2 in, same 4-1/2 in length, same loop ends — "
     "0.031 in apart and visually identical in a bag.\n\n"
     "THIS part is McMaster MUSIC WIRE (ASTM A228): high-carbon, holds its "
     "rate. #1132 is zinc-plated retail and will take a set under sustained "
     "load. Do not let one satisfy a call for the other.\n\n"
     "STILL UNSEEN as of 2026-08-26. It has not turned up on the bench during "
     "the wire-shelf walk, and the card that resembles it is NOT it. This row "
     "stays unlocated until the actual McMaster bag is found.")

for pk, add in ((1132, A), (977, B)):
    p = Part.objects.get(pk=pk)
    print(f"[{pk}] {p.name[:60]}")
if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

for pk, add in ((1132, A), (977, B)):
    p = Part.objects.get(pk=pk)
    if "1/32 IN APART" not in (p.notes or "") and "NEAR-TWIN EXISTS" not in (p.notes or ""):
        Part.objects.filter(pk=pk).update(notes=(p.notes or "").rstrip() + add)
        print(f"  annotated [{pk}]")

Part.objects.filter(pk=1132).update(
    description="Extension spring, LOOP ends, 15/32 in OD x 4-1/2 in x .041 in "
                "wire, zinc, max safe load 5.28 lb. Retail card of 2 (P-9602). "
                "Low-grade — not music wire. Near-twin of #977, which is.")
print("done")
