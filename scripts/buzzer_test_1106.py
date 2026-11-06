"""Record Scott's 3.3 V bench test of the buzzer modules (2026-11-06).

Green #1517: + to 3.3 V, - to ground, OUT tied to ground -> buzzes. A buzzer that
sounds from a DC level drives itself, so it is ACTIVE; OUT is an active-low INPUT
despite its label. OUT high and OUT floating were not reported, so they are not
written as "silent". Blue #1516 not tested yet.
Dry run by default.  itq run scripts/buzzer_test_1106.py [--commit]"""
import os, sys
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django; django.setup()
from part.models import Part
from plugins.notes_compat import note_append, note_text

PK = 1517
# The 11-06 description was cut at 250 chars mid-sentence, so it is rewritten whole, not patched.
DESC = ("ACTIVE buzzer, LOW-level trigger: OUT is an input, tie to GND to sound (Scott, 3.3 V, 2026-11-06). "
        "Green board, sealed 12 mm buzzer, SOT-23 transistor, 200R + 5.1k, cap. Pins + / OUT / - "
        "(NOT the MH-FMD order).")
NOTE = ("## Bench test 2026-11-06 (Scott)\n\n3.3 V supply. + to 3.3 V, - to ground, OUT tied to ground: it buzzes. "
        "Sound from a DC level means the buzzer drives itself, so ACTIVE; OUT is an active-low input "
        "despite its name. OUT high and OUT floating: not reported.")
p = Part.objects.get(pk=PK)
assert p.description.startswith("Green buzzer board"), p.description
desc = DESC
assert len(desc) <= 250, len(desc)
print(len(desc), desc)
if "--commit" not in sys.argv:
    print("DRY RUN"); sys.exit(0)
Part.objects.filter(pk=PK).update(description=desc[:250])
if "Bench test 2026-11-06" not in note_text(p):
    note_append(p, NOTE)
p = Part.objects.get(pk=PK)
ok = p.description == desc and "Bench test 2026-11-06" in note_text(p)
print("VERDICT:", "SUCCESS" if ok else "FAILED")
