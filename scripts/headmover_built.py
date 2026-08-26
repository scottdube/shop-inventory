"""The head mover was BUILT and is on the machine. Photo, 2026-08-26.

Written minutes after the project record was created saying "status unknown".
It is not unknown: Scott photographed it installed on the mill/drill.

WHAT THE PHOTO SHOWS: a large aluminium plate sprocket -- lightening holes,
looks shop-cut rather than bought -- driven by roller chain off a motor mounted
under the head, through a steel bracket plate bolted to the column casting. The
head, quill and chuck are all in place. The machine is in the shop, in service,
green, with the acme leadscrew and rack visible along the column.

THREE THINGS THIS SETTLES:

1. The project is BUILT, not abandoned. The bearings still on the shelf are
   LEFTOVERS from it, not parts reserved for it.
2. "Used on repair projects" (Scott, on the zeroed thrust bearing sets) almost
   certainly means FITTED TO THIS. A head's weight is an axial load, which is
   exactly what a needle thrust bearing is for and exactly what a deep-groove
   ball bearing will not take. Two shaft sizes were bought, 3/8" and 7/8".
3. The big sprocket is NOT the #1042 ANSI 35 9-tooth one. That one is small and
   3/8" bore -- it is the DRIVE end. The photographed sprocket is the driven
   end and appears to be shop-made, so it will never appear in purchase history
   and is not a missing part.

AND: THIS MACHINE IS NOT IN THE SHOP DOCUMENTATION. Nineteen machines are
catalogued and the mill/drill carrying a custom powered head is not one of
them. That is a documentation gap, not an inventory one, and it is why the
2022 purchases looked homeless -- the thing they were bought for does not
exist anywhere in the written record.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

NEWNAME = "Jet Mill/Drill Automated Head Mover (2022, built and in service)"
p = Part.objects.get(pk=1126)
print(f"[{p.pk}] {p.name}\n  -> {NEWNAME}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

if p.name != NEWNAME:
    p.name = NEWNAME
    p.save()

add = ("\n\n---\n\n**BUILT AND IN SERVICE — confirmed by photograph "
       "2026-08-26.**\n\n" + __doc__.split("WHAT THE PHOTO SHOWS:")[1]
       .replace("THREE THINGS THIS SETTLES:", "**Three things this settles:**")
       .replace("AND: THIS MACHINE IS NOT IN THE SHOP DOCUMENTATION.",
                "**AND: THIS MACHINE IS NOT IN THE SHOP DOCUMENTATION.**"))
add = "WHAT THE PHOTO SHOWS:" + add if False else add
p.refresh_from_db()
if "BUILT AND IN SERVICE" not in (p.notes or ""):
    Part.objects.filter(pk=1126).update(
        notes=(p.notes or "").rstrip() + "\n\n---\n\n**BUILT AND IN SERVICE — "
        "confirmed by photograph 2026-08-26.**\n\nA large aluminium plate "
        "sprocket with lightening holes — shop-cut, not bought — driven by "
        "roller chain from a motor under the head, through a steel bracket "
        "plate bolted to the column casting. Head, quill and chuck all in "
        "place. Machine is in the shop and in service.\n\n"
        "**The bearings still on the shelf are LEFTOVERS from this build, not "
        "parts reserved for it.** That is the difference between surplus and "
        "committed stock and it was not knowable an hour ago.\n\n"
        "**'Used on repair projects'** — Scott's phrase for the zeroed thrust "
        "bearing sets — almost certainly means FITTED TO THIS. A mill head's "
        "weight is an axial load: exactly what a needle thrust bearing is for, "
        "and exactly what a deep-groove ball bearing will not take. Two shaft "
        "sizes were bought, 3/8in and 7/8in.\n\n"
        "**The photographed sprocket is not #1042.** That one is ANSI 35, nine "
        "teeth, 3/8in bore — small, and the DRIVE end. The big driven sprocket "
        "looks shop-made, so it will never appear in purchase history and is "
        "not a missing part.\n\n"
        "**THIS MACHINE IS NOT IN THE SHOP DOCUMENTATION.** Nineteen machines "
        "are catalogued and the mill/drill carrying a custom powered head is "
        "not one of them. That is a documentation gap, not an inventory one — "
        "and it is precisely why the 2022 purchases looked homeless: the thing "
        "they were bought for does not exist anywhere in the written record.")

# the tag on member parts says "probably bought for" -- upgrade the ones that
# are now known leftovers rather than speculative.
for pk in (1042, 1041, 1011, 1010, 1123, 1121, 1124, 1021, 1022, 1018, 1019):
    q = Part.objects.get(pk=pk)
    if "BUILD CONFIRMED" not in (q.notes or ""):
        Part.objects.filter(pk=pk).update(notes=(q.notes or "").rstrip() +
            "\n\nBUILD CONFIRMED 2026-08-26: the head mover exists and is on "
            "the machine. So this is LEFTOVER from a finished build, not stock "
            "committed to an unfinished one — free to use elsewhere.")

p.refresh_from_db()
print(f"\n[{p.pk}] {p.name}")
