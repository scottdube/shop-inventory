"""Silicone confirmed by hand. The record was right; the doubt was mine."""
import os, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockItem, StockLocation

COMMIT = "--commit" in sys.argv
TODAY = date.today()

ADD = (f"\n\n--- MATERIAL CONFIRMED {TODAY} ---\n"
       "Scott flexed one: SILICONE. The 'soft silicone' in the part description "
       "was correct all along, and so is the name. The doubt came from a "
       "photograph, where semi-rigid orange plastic and soft silicone look "
       "identical - a photograph shows identity, not material.")
RB22 = ("Two NEWISHTOOL orange silicone squeegee cards (#791), located here "
        "2026-08-25 and material confirmed by hand the same day. FREE STORAGE, "
        "not a project kit. Loose hand tools belong on the wall by the rack's "
        "own rule, so this bin is a candidate to empty once they have a home.")

si = StockItem.objects.get(pk=94)
print(f"stock #{si.pk} @ {si.location.pathstring}")
print(f"  append {len(ADD)} chars; RB-22 -> {len(RB22)} chars")
if not COMMIT:
    print("\n  DRY RUN - add --commit"); sys.exit()

StockItem.objects.filter(pk=94).update(notes=si.notes + ADD)
StockLocation.objects.filter(name="RB-22").update(description=RB22)
si = StockItem.objects.get(pk=94)
print("  notes:", "OK" if si.notes.endswith(ADD) else "MISMATCH")
print("  RB-22:", "OK" if StockLocation.objects.get(name='RB-22').description == RB22 else "MISMATCH")
