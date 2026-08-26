"""Record the 2022 Jet mill/drill head-mover build, and tag its parts.

Scott, 2026-08-26, on why a cluster of chain-drive and thrust hardware was
bought through 2022 and never filed: "I think it was the automated head mover
for the Jet Mill Drill."

That single sentence explains ten homeless rows. Written down immediately
because it is exactly the kind of fact that is obvious to one person for about
a year and then unrecoverable -- no drawing, no BOM, no note, and the machine
itself is not in the catalogue or the shop docs.

THE CLUSTER, by purchase date:

  2022-02-01  PO-0130  ANSI 35 sprocket, 9T, 3/8" bore      #1042
  2022-02-01  PO-0130  nylon sleeve bearing, 3/8"           #1041
  2022-06-01           R6-2RS ball bearings x10 (Amazon)    #1123
  2022-06-01           HIAORS 10mm chain roller (Amazon)    -- same day
  2022-08-01  PO-0126  needle thrust bearing 3/8" + washers #1021 #1022
  2022-10-04  PO-0125  needle thrust bearing 7/8" + washers #1018 #1019
  2022-11-10           6203-2RS x2 (XiKe, Amazon)           #1121
  2022-11-19           Timken 6203-2RSC3 (Amazon)
  2022-12-11           30203 tapered rollers x5 (Amazon)    #1124

Chain drive, thrust bearings in two shaft sizes, a rod end, shaft collar, and
3/8" shafting. A leadscrew or pinion raising and lowering a mill head is
exactly what wants thrust bearings -- a head's weight is an axial load, and a
deep-groove ball bearing will not take it.

The thrust bearing sets are the ones Scott said were "used on repair projects"
and they are already zeroed. Read against this, "used" most likely means FITTED
TO THIS BUILD, which is a better record than "consumed somewhere".

**THE MACHINE IS NOT IN THE CATALOGUE OR THE SHOP DOCS.** If the Jet is gone --
displaced by the Tormach 1100MX -- then this is a dead project and everything
above is surplus rather than reserved. That question is OPEN and it changes what
should happen to the parts, so it is recorded here rather than assumed.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

NAME = "Jet Mill/Drill Automated Head Mover (2022, status unknown)"
DESC = ("Powered head raise/lower for the Jet mill-drill, bought through 2022 "
        "and never recorded. Chain drive plus thrust bearings. Whether it was "
        "built, and whether the machine is still here, is unresolved.")
NOTES = __doc__.split("THE CLUSTER, by purchase date:")[1]
NOTES = ("**2022 build, reconstructed from purchase history 2026-08-26.**\n\n"
         "Scott: *\"I think it was the automated head mover for the Jet Mill "
         "Drill.\"* That one sentence accounts for ten stock rows that had no "
         "home and no explanation.\n\nTHE CLUSTER, by purchase date:" + NOTES)

MEMBERS = {
    1042: "ANSI 35 sprocket, 9T, 3/8in bore",
    1041: "nylon sleeve bearing, 3/8in",
    1011: "ball joint rod end, 1/4-28",
    1010: "set screw shaft collar, 1/4in",
    1123: "R6-2RS x10",
    1121: "6203-2RS",
    1124: "30203 tapered rollers",
    1021: "needle thrust bearing 3/8in (consumed)",
    1022: "washers for the 3/8in thrust bearing (consumed)",
    1018: "needle thrust bearing 7/8in (consumed)",
    1019: "washers for the 7/8in thrust bearing (consumed)",
}

print(f"project: {NAME}")
print(f"tagging {len(MEMBERS)} parts")
if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

proj = Part.objects.filter(name=NAME).first()
if not proj:
    proj = Part.objects.create(name=NAME, description=DESC, category_id=132,
                               assembly=True, purchaseable=False, active=True)
    print(f"created part [{proj.pk}]")
Part.objects.filter(pk=proj.pk).update(notes=NOTES)

TAG = "PROBABLY BOUGHT FOR THE JET MILL/DRILL HEAD MOVER"
for pk, why in MEMBERS.items():
    p = Part.objects.filter(pk=pk).first()
    if not p or TAG in (p.notes or ""):
        continue
    Part.objects.filter(pk=pk).update(notes=(p.notes or "").rstrip() +
        f"\n\n{TAG} (#{proj.pk}), the 2022 build reconstructed from purchase "
        f"history on 2026-08-26 — this part is the {why}. That is an inference "
        f"from purchase DATE and function, not a record: no BOM exists. It "
        f"explains why the part was bought and never filed, and it is the first "
        f"place to look before assuming this is general stock.")
    print(f"  tagged [{pk}] {p.name[:52]}")

proj.refresh_from_db()
print(f"\n[{proj.pk}] {proj.name}")
