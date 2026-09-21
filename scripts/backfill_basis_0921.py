"""For each line of the PFD BOM, what is the COUNT BASIS of the stock behind it?

Backfilling the MFD's consumption is only safe per line, and the deciding
question is whether that part has been physically COUNTED since the MFD was
built. Tallied rows already exclude what the MFD ate; uncounted rows still
contain it. Treating the two the same is how a backfill wrecks counts.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, BomItem
from stock.models import StockItem

tally = {"TALLIED": 0, "ESTIMATE": 0, "UNKNOWN": 0}
print("%-6s %-42s %8s  %s" % ("part", "name", "onhand", "basis"))
for bi in BomItem.objects.filter(part_id=1137).order_by("sub_part__pk"):
    p = bi.sub_part
    rows = list(StockItem.objects.filter(part=p))
    onhand = sum(float(r.quantity) for r in rows)
    notes = " ".join((r.notes or "") for r in rows)
    dated = any(r.stocktake_date for r in rows)
    if "[ESTIMATE]" in notes or "NOT COUNTED" in notes.upper():
        basis = "ESTIMATE - still contains what the MFD ate"
    elif "COUNTED" in notes.upper() and dated:
        basis = "TALLIED - MFD's parts already gone from this number"
    else:
        basis = "UNKNOWN - no count marker either way"
    tally[basis.split(" ")[0]] += 1
    print("#%-5s %-42s %8.0f  %s  need %s" % (p.pk, p.name[:42], onhand, basis, bi.quantity))
print("\n%s" % tally)
