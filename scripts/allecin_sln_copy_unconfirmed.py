"""Mark the SLN copies of the two ALLECIN kits as UNCONFIRMED (2026-10-23).

The 'owned at two sites' claim on #1 and #6 was inferred from purchase history:
each kit was ordered twice, and one order of each shipped to LRD (#448, #371).
Asked on 2026-10-23 whether an SLN copy exists, Scott said he doesn't remember,
and he is at LRD until ~June 2027. So the claim is a lead from the orders, not
something anyone has seen. The note says that, and it is not to be asked again
(see dont-reask-unknowns); the check waits for SLN, listed in docs/OPEN.md.

    itq run scripts/allecin_sln_copy_unconfirmed.py            # dry run
    itq run scripts/allecin_sln_copy_unconfirmed.py --commit
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from plugins.notes_compat import note_text, note_append

MARK = "SLN COPY UNCONFIRMED 2026-10-23"
TEXT = (f"=== {MARK} ===\nThe 'copy at SLN' above is INFERRED from purchase "
        "history (two orders, one shipped to LRD), not seen. Asked 2026-10-23, "
        "Scott doesn't remember having one, and he is at LRD until ~June 2027. Do "
        "not ask again. Look for it when back at SLN (docs/OPEN.md, 'Check at SLN "
        "next season'). Until then, the only copy known to exist is the LRD one in "
        "Cab2-D3.")

for pk in (1, 6):
    p = Part.objects.get(pk=pk)
    have = MARK in note_text(p)
    print(f"#{pk} {p.name[:60]} — {'already marked' if have else 'will mark'}")
    if have or "--commit" not in sys.argv:
        continue
    note_append(p, TEXT)
    ok = MARK in note_text(Part.objects.get(pk=pk))
    print("  VERIFIED" if ok else "  *** VERIFY FAILED ***")
