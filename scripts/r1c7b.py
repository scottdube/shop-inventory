"""Three more identifiable push buttons out of the R1C7 tray.

Also drops the C&K 8168 mention from the 'Assorted' record now that it has a
part of its own - leaving it in both places would double-count it in a search.
"""
import argparse, os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

cat = Part.objects.get(pk=98).category

NEW = [
    ("ALCO MPG-101 Push Button", None,
     "**ALCO** (Alcoswitch) MPG-series miniature push button, panel mount, "
     "threaded bushing with hex nut and black plunger cap.\n\n"
     "Body stamped `MPG 101 F9 ALCO`. Blue moulded base, **3 gold-plated "
     "terminals** (so SPDT, not a simple 2-terminal button).\n\n"
     "`F9` is most likely a date or variant suffix rather than part of the part "
     "number - not verified."),
    ("C&K 8168 Push Button with Panel Bezel", None,
     "**C&K** (USA) 8168 push button, red moulded body, **3 terminals**, fitted "
     "with a black rectangular **panel bezel / actuator frame** - so it mounts "
     "through a square cutout rather than a round hole.\n\n"
     "Body stamped `8168 C&K U.S.A.`\n\n"
     "The bezel is the distinguishing feature: this is a panel-front button, not "
     "a bushing-mount one."),
    ("TEC SBL-66 Push Button", None,
     "**TEC** SBL-series push button. Black cylindrical body, knurled bushing, "
     "large black cap, **3 gold-plated pins** on the rear.\n\n"
     "Body stamped with the TEC shield mark and `SBL` / `66`. Read as "
     "**SBL-66**; the `66` could equally be a date or variant code - not "
     "verified against a TEC catalogue.\n\n"
     "Substantial, well-made parts - worth identifying properly if one is ever "
     "needed for a design."),
]

for name, ipn, note in NEW:
    p = Part.objects.filter(name=name).first()
    if p:
        print(f"  exists  #{p.pk}  {name}")
        continue
    print(f"  CREATE          {name}")
    if a.commit:
        p = Part.objects.create(
            name=name[:100], IPN=ipn or "", category=cat,
            description=note.split("\n")[0].replace("**", "")[:250], notes=note,
            active=True, component=True, purchaseable=True)
        print(f"          -> #{p.pk}")

q = Part.objects.filter(pk=750).first()
if q and "C&K 8168" in (q.notes or ""):
    print("\n  #750: dropping the C&K 8168 mention - it has its own part now")
    if a.commit:
        q.notes = q.notes.replace(
            "A few black bodies. One is marked **C&K 8168**.",
            "A few black bodies. (The C&K 8168, ALCO MPG-101, TEC SBL-66 and NKK "
            "NS-196/197 that were in this tray now have their own records - this "
            "bucket is only the unmarked remainder.)")
        q.save()

print(f"\n{'WROTE' if a.commit else 'DRY RUN'}")
