"""Second round of Scott's 3.3 V buzzer bench test (2026-11-06).

Blue #1516 MH-FMD, as Scott reported it: I/O floating -> nothing; I/O to VCC ->
nothing; I/O to ground -> a short tone, about a second, then silent although
still grounded. Green #1517: floating -> nothing (adds to round 1).

What it MEANS is not established, so the record keeps the observation apart
from the reading. Most likely PASSIVE: a passive buzzer sounds only on edges, and
a hand-held jumper bouncing on the pin makes a burst of edges that reads as a
short tone. An active buzzer would keep sounding while I/O stays low. A
2-4 kHz PWM on I/O (steady tone = passive) settles it; not done.
#1516's description is rewritten whole: the 11-06 run had cut it at 250 chars.
Dry run by default.  itq run scripts/buzzer_test_1106b.py [--commit]"""
import os, sys
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django; django.setup()
from part.models import Part
from plugins.notes_compat import note_append, note_text

BLUE, GREEN = 1516, 1517
DESC = ("Probably PASSIVE (not confirmed): at 3.3 V, I/O to GND gives ~1 s of sound then silence; "
        "high or floating = silent (Scott 2026-11-06). Needs 2-4 kHz PWM on I/O. Blue MH-FMD, "
        "SOT-23 transistor, 1k. Pins GND / I/O / VCC.")
assert len(DESC) <= 250, len(DESC)
BNOTE = ("## Bench test 2026-11-06 (Scott)\n\n3.3 V supply, VCC to 3.3 V, GND to ground.\n\n"
         "| I/O | Result |\n|---|---|\n| floating | nothing |\n| to VCC | nothing |\n"
         "| to ground | short tone, about a second, then silent although still grounded |\n\n"
         "**Reading (not established):** probably a PASSIVE buzzer. A passive one sounds only on edges, "
         "and a hand-held jumper bouncing on the pin makes a burst of edges; an active one would keep "
         "sounding while I/O stays low. Settle it with a 2-4 kHz PWM on I/O: a steady tone = passive.")
GKEY = "Floating (round 2)"
GNOTE = f"{GKEY}, 2026-11-06 (Scott): OUT floating -> nothing. OUT to VCC still not reported."

b, g = Part.objects.get(pk=BLUE), Part.objects.get(pk=GREEN)
assert b.name.startswith("Buzzer Module MH-FMD") and g.name.startswith("Buzzer Module, 3-pin"), (b.name, g.name)
print(len(DESC), DESC)
if "--commit" not in sys.argv:
    print("DRY RUN"); sys.exit(0)
Part.objects.filter(pk=BLUE).update(description=DESC)
if "Bench test 2026-11-06" not in note_text(b):
    note_append(b, BNOTE)
if GKEY not in note_text(g):
    note_append(g, GNOTE)
b, g = Part.objects.get(pk=BLUE), Part.objects.get(pk=GREEN)
ok = b.description == DESC and "Bench test 2026-11-06" in note_text(b) and GKEY in note_text(g)
print("VERDICT:", "SUCCESS" if ok else "FAILED")
