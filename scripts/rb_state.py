"""Red Bins walk board: one line per bin, what's in it, what's counted.

Exists because the walk kept starting with "which bin next?" and the answer
lived in three places -- OPEN.md prose, the location description, and the
stock rows. This reads the database, which is the only one that stays true.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockItem, StockLocation

# The rack's boilerplate description is the DEFAULT text every bin was created
# with. It is not a declaration -- a bin carrying only this has never been
# opened. Treating it as "declared" made eleven unopened bins read as finished.
BOILERPLATE = "Red bin. Holds ONE project's kit OR free storage - never both."

rack = StockLocation.objects.filter(name__iexact="Red Bins").first()
if rack is None:
    sys.exit("no location named 'Red Bins'")
print(f"RACK: {rack.pathstring}  #{rack.pk}")
if rack.description:
    print(f"  {rack.description}")
print()

bins = sorted(rack.get_children(), key=lambda l: l.name)
for b in bins:
    rows = list(StockItem.objects.filter(location=b))
    counted = sum(1 for r in rows if r.stocktake_date)
    desc = (b.description or "").strip()
    if desc == BOILERPLATE:
        desc = ""
    if rows:
        state = f"{len(rows)} row(s), {counted} counted"
    elif desc:
        state = "DECLARED (description, no rows)"
    else:
        state = "NEVER OPENED"
    print(f"{b.name:<8} {state}")
    if desc:
        print(f"         “{desc[:110]}”")
    for r in rows:
        mark = r.stocktake_date.isoformat() if r.stocktake_date else "NEVER COUNTED"
        est = " [ESTIMATE]" if "[ESTIMATE]" in (r.notes or "") else ""
        print(f"         #{r.part.pk:<5} qty {r.quantity:<8g} {r.part.name[:52]:<52} {mark}{est}")
    print()

print(f"{len(bins)} bins")
# RB-14 counts five rows, all stamped, and also holds a jig nobody catalogued.
# A count is per-ROW; completeness is per-CONTAINER, and nothing here measures
# the second. Say so, rather than letting a green line read as "done".
print("\nCOUNTED means the rows are right. It does NOT mean the bin's contents")
print("are all on the books - only a person at the open bin can say that.")
