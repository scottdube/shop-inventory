"""Scott's expectation about the gauge thread, recorded AS an expectation."""
import os, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockItem

COMMIT = "--commit" in sys.argv
ADD = (f"\n\n--- EXPECTED, NOT VERIFIED, {date.today()} ---\n"
       "Scott: he thinks the gauge has BOTH threads - the larger one on the "
       "gauge with a BUSHING stepping it down to the smaller - and will check "
       "when he is next in the lab. Recorded as an expectation, not a "
       "measurement; it does not settle the thread question above.\n\n"
       "It is plausible on the listing evidence: MEANLIN ships at least one "
       "gauge in this family explicitly 'with Stainless Steel Hex Bushing'. "
       "That variant is the -30inHG~60Psi 1/4in NPT, a different range from "
       "this gauge, so it corroborates the practice and not this unit.\n\n"
       "If it is a 1/4 NPT gauge in a 1/8 bushing, BOTH numbers matter and "
       "they are different facts: what the gauge is, and what it currently "
       "presents to a fitting. Record both, and say which is which.")

si = StockItem.objects.filter(part_id=1097).first()
print(f"stock #{si.pk}: append {len(ADD)} chars")
if not COMMIT:
    print("  DRY RUN - add --commit"); sys.exit()
StockItem.objects.filter(pk=si.pk).update(notes=si.notes + ADD)
si = StockItem.objects.get(pk=si.pk)
print("  VERIFIED" if si.notes.endswith(ADD) else "  MISMATCH")
