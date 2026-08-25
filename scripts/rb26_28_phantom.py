"""RB-26, RB-27, RB-28 are labels, not bins.

Scott, 2026-08-25: "26, 27, 28 do not exist except as labels." The rack holds
RB-01..RB-25. Three locations were created because three labels were printed,
and the walk has been carrying them as unopened bins ever since.

Marked STRUCTURAL rather than deleted. Structural locations cannot hold stock,
so the phantom can never receive a part by mistake, and the record that three
labels were made survives -- which is the thing somebody needs if three more
bins are ever bought.
"""
import os, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockItem, StockLocation

COMMIT = "--commit" in sys.argv
TODAY = date.today()
NAMES = ["RB-26", "RB-27", "RB-28"]
DESC = (f"NOT A PHYSICAL BIN - label only. Scott, {TODAY}: the rack holds "
        "RB-01..RB-25; labels were printed through RB-28 and the last three "
        "have no bin behind them. Marked STRUCTURAL so nothing can be filed "
        "here. If three more bins are ever added, clear the structural flag "
        "and the label is already made.")

for n in NAMES:
    loc = StockLocation.objects.get(name=n)
    rows = StockItem.objects.filter(location=loc).count()
    kids = loc.get_children().count()
    print(f"{n} #{loc.pk}: rows={rows} children={kids} structural={loc.structural}")
    if rows or kids:
        sys.exit(f"{n} is not empty - refusing")

if not COMMIT:
    print(f"\n  would set structural=True + description ({len(DESC)} chars)")
    print("  DRY RUN - add --commit")
    sys.exit()

StockLocation.objects.filter(name__in=NAMES).update(structural=True, description=DESC)
for n in NAMES:
    loc = StockLocation.objects.get(name=n)
    ok = loc.structural and loc.description == DESC
    print(f"  {n}: structural={loc.structural} {'OK' if ok else 'MISMATCH'}")
