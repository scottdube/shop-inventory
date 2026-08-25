"""BO-0013's reference_int says 25, so the next build came out BO-0026.

Found 2026-08-25 while creating the water-valve build: it was issued BO-0026,
skipping twelve numbers. The cause is not the new build. `generate_reference()`
takes the next number from MAX(reference_int), and BO-0013 carries
reference_int=25 against a reference that reads 0013 -- the two fields have
diverged, so every future build inherits the jump.

Same family as the PO reference_int trap already in TRAPS.md, and milder only
by luck: there the clamp was to int32 max and generate_reference() was broken
permanently.

Fix: put reference_int back in agreement with the reference it belongs to, then
renumber the new build into the gap it should have had.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from build.models import Build

COMMIT = "--commit" in sys.argv

bad = Build.objects.get(reference="BO-0013")
new = Build.objects.get(reference="BO-0026")
print(f"BO-0013 reference_int={bad.reference_int} -> 13")
print(f"BO-0026 -> BO-0014, reference_int={new.reference_int} -> 14")

if Build.objects.filter(reference="BO-0014").exists():
    sys.exit("BO-0014 already exists - stop")

if not COMMIT:
    print("\n  DRY RUN - add --commit")
    sys.exit()

# queryset update, not save(): save() on this install has reported success and
# written nothing, and reference is format-validated on the model.
Build.objects.filter(pk=bad.pk).update(reference_int=13)
Build.objects.filter(pk=new.pk).update(reference="BO-0014", reference_int=14)

for pk, ref, ri in [(bad.pk, "BO-0013", 13), (new.pk, "BO-0014", 14)]:
    b = Build.objects.get(pk=pk)
    print(f"  {b.reference} reference_int={b.reference_int} "
          f"{'OK' if b.reference == ref and b.reference_int == ri else 'MISMATCH'}")

print("\nall builds:")
for b in Build.objects.all().order_by("reference_int"):
    flag = "" if b.reference == f"BO-{b.reference_int:04d}" else "   <-- DIVERGED"
    print(f"  {b.reference:10s} ref_int={b.reference_int}{flag}")
