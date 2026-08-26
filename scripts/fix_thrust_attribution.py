"""The thrust bearings went into a VISE REBUILD, not the head mover.

Scott, 2026-08-26: "thrust bearings were used in a vise rebuild at least the
big one was."

I had attributed all four rows to the Jet mill/drill head mover, and the
reasoning was clean: a mill head's weight is an axial load, needle thrust
bearings take axial load, deep-groove ball bearings do not, and the purchases
sat inside the same 2022 cluster as the chain drive.

**Every step of that was true and the conclusion was wrong.**

A vise screw is also an axial load -- a far bigger one, and a thrust washer
stack behind the screw nut is the classic vise rebuild. The reasoning never
distinguished between the two applications; it just found the first one that
fitted and stopped.

WHAT PURCHASE-DATE CLUSTERING ACTUALLY BUYS YOU: it groups parts by WHEN, and
then the mind supplies a WHY. A busy shop runs several jobs in the same months,
so a date cluster is evidence of a PERIOD, not of a PROJECT. It is a lead. It
is not a bill of materials.

Corrected here:
  #1018  7/8" needle thrust bearing   -> VISE REBUILD, stated by Scott
  #1019  its 0.032" washers           -> VISE REBUILD, same set
  #1021  3/8" needle thrust bearing   -> UNKNOWN. "at least the big one" leaves
  #1022  its 0.032" washers              the small set unattributed, and an
                                         unattributed part is a better record
                                         than a confidently misattributed one.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

VISE = ("\n\n---\n\nATTRIBUTION CORRECTED 2026-08-26. **This went into a VISE "
        "REBUILD**, stated by Scott. It was recorded earlier the same day as "
        "part of the Jet mill/drill head mover (#1126) — that was an inference "
        "from purchase date and from 'thrust bearing implies axial load', and "
        "it was wrong.\n\n"
        "A vise screw is an axial load too, and a bigger one than a mill head. "
        "A thrust washer stack behind the screw nut is the standard vise "
        "rebuild. The reasoning found the first application that fitted and "
        "stopped.")

UNKNOWN = ("\n\n---\n\nATTRIBUTION RETRACTED 2026-08-26. Recorded earlier the "
           "same day as part of the Jet mill/drill head mover (#1126). That was "
           "an inference from purchase date, and its companion set (#1018 / "
           "#1019, the 7/8\") turned out to be a VISE REBUILD instead.\n\n"
           "Scott said \"at least the big one was\", which leaves THIS set "
           "genuinely unknown. Recorded as unknown rather than reassigned to "
           "the vise: the 3/8\" set was bought on a different order two months "
           "earlier than the 7/8\", so there is no reason beyond tidiness to "
           "assume they went to the same job.")

TAGS = {1018: VISE, 1019: VISE, 1021: UNKNOWN, 1022: UNKNOWN}

for pk in TAGS:
    p = Part.objects.get(pk=pk)
    print(f"[{pk}] {p.name[:60]}")
if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

for pk, tag in TAGS.items():
    p = Part.objects.get(pk=pk)
    if "ATTRIBUTION" not in (p.notes or ""):
        Part.objects.filter(pk=pk).update(notes=(p.notes or "").rstrip() + tag)
        print(f"  corrected [{pk}]")

# and the project's own claim about them
proj = Part.objects.get(pk=1126)
if "OVERREACHED" not in (proj.notes or ""):
    Part.objects.filter(pk=1126).update(notes=(proj.notes or "").rstrip() +
        "\n\n---\n\n**THIS RECORD OVERREACHED, corrected 2026-08-26.** The four "
        "needle thrust bearing rows (#1018 #1019 #1021 #1022) were claimed for "
        "this build and do not belong to it. Scott: the 7/8in set went into a "
        "VISE REBUILD, and the 3/8in set is unknown.\n\n"
        "The mistake is worth keeping visible because the reasoning was sound: "
        "a mill head's weight IS axial, thrust bearings DO take axial load, and "
        "the purchases DID sit in the same 2022 cluster. It simply never asked "
        "what else in the shop takes an axial load — and a vise screw takes a "
        "much bigger one.\n\n"
        "**A purchase-date cluster groups parts by WHEN, and the mind supplies "
        "the WHY.** A shop runs several jobs in the same months, so a cluster "
        "is evidence of a PERIOD, not of a project. Treat it as a lead worth "
        "asking a person about — which is how this one was caught — never as a "
        "bill of materials.\n\n"
        "What survives: the chain drive parts, which Scott named directly, and "
        "the photograph of the machine.")

print("\nverify:")
for pk in list(TAGS) + [1126]:
    p = Part.objects.get(pk=pk)
    flag = "VISE" if "VISE REBUILD**" in (p.notes or "") else (
           "UNKNOWN" if "ATTRIBUTION RETRACTED" in (p.notes or "") else
           "OVERREACH NOTED" if "OVERREACHED" in (p.notes or "") else "?")
    print(f"  [{pk}] {flag:<16} {p.name[:52]}")
