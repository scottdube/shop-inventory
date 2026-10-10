"""Part #1385 "Steel Setup Block, drilled" is a SINE BAR -- Scott's tape photo,
2026-10-10, shows a ground roll at each end, which the first (top-down) photo
hid. Body ~6 in on the tape with the rolls inset from the ends: a 5 in sine bar
(5 in roll centres is the standard size for a ~6 in body). The 5 in is read off a
tape-measure photo, not gauged -- noted on the part. Same photo confirms the
wooden-case test bar at ~272-275 mm, matching part #1364.

    itq run scripts/sine_bar_1010.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part  # noqa: E402

p = Part.objects.get(pk=1385)
print(f"part #{p.pk} {p.name}")
assert p.name in ("Steel Setup Block, drilled", "Sine Bar, 5 in"), p.name
if "--commit" not in sys.argv:
    sys.exit("DRY RUN -- add --commit")
Part.objects.filter(pk=1385).update(
    name="Sine Bar, 5 in",
    description="Sine bar, 5 in roll centres, ~6 in body, 4 lightening holes through the side, "
                "6 holes in the top face",
    keywords="sine bar, 5 inch, angle setting, gauge blocks, metrology, roll",
    notes=("Filed 2026-10-10 from Scott's photos of the metrology-bench items; first "
           "filed as a drilled setup block until a second photo showed the rolls.\n\n"
           "**5 in is read from a tape-measure photo** (body ~6 in), not gauged -- "
           "check roll centres with gauge blocks before trusting an angle. Maker unknown, no PO."))
p.refresh_from_db()
assert p.name == "Sine Bar, 5 in", p.name
print(f"-> {p.name}")
