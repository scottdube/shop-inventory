"""Retitle the two G1000 build orders so neither can be misread.

Scott, 2026-09-21, looking at the build list: "there is a g1000 build and a
g1000 mfd build with only 1 part... I don't know which is which."

He is right and the list caused it. docs/G1000.md settles the identities from
his own 2026-08-29 count of the physical pile: MFD right = BUILT, PFD left =
TO BUILD. So BO-0017 "Sim G1000" (Pending, 24 lines, kit bagged for Florida)
is the PFD, and BO-0020 is the MFD.

Two renames, no data changes:

  BO-0017  "Sim G1000"      -> "Sim G1000 PFD"
  BO-0020  "Sim G1000 MFD"  -> "Sim G1000 MFD - consumption record"

The second is the important one. BO-0020 holds 1 of the ~24 parts the MFD
actually consumed, because the count established exactly one: the nav switch.
Its part description already says "not a designed assembly - a container for
what it consumed", but nobody reads a part description while scanning a build
list. The title has to carry it.

Rejected building the MFD's real 24-line BOM: every line but the switch would
be inferred from the PFD's BOM rather than counted, which is the failure
docs/G1000.md already records three times ("stop deriving quantities from
receipts"). Rejected deleting BO-0020: the switch really was consumed, and the
allocation is the only place that fact is recorded.

Part #1137 is deliberately NOT renamed - its description says the scope is not
yet fixed by Scott, and naming it PFD is a scope decision, not a label fix.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from build.models import Build

COMMIT = "--commit" in sys.argv
PLAN = {
    "BO-0017": ("Sim G1000", "Sim G1000 PFD"),
    "BO-0020": ("Sim G1000 MFD", "Sim G1000 MFD - consumption record"),
}

for ref, (expect, new) in PLAN.items():
    b = Build.objects.get(reference=ref)
    print("%s  %-38r -> %r" % (ref, b.title, new))
    if b.title != expect:
        print("   ABORT: title is not %r, someone else changed it" % expect)
        sys.exit(1)

if not COMMIT:
    print("\nDRY RUN - add --commit")
    sys.exit()

for ref, (expect, new) in PLAN.items():
    b = Build.objects.get(reference=ref)
    b.title = new
    b.save()

print("\n=== re-read ===")
for ref in PLAN:
    b = Build.objects.get(reference=ref)
    ok = b.title == PLAN[ref][1]
    print("  %s %-44r %s" % (ref, b.title, "OK" if ok else "WRITE DID NOT STICK"))
    if not ok:
        Build.objects.filter(reference=ref).update(title=PLAN[ref][1])
        print("     fell back to queryset update -> %r"
              % Build.objects.get(reference=ref).title)
