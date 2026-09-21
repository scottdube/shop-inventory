"""Close the "STILL OPEN" paragraph on stock row 9 (RKJXT nav switch).

It asked where the surviving switch goes and said not to file it without
asking. Answered 2026-09-21 from docs/G1000.md, which records Scott's own
2026-08-29 count of the physical pile: MFD right = BUILT, PFD left = TO BUILD.
So this unit is in the built MFD in the cockpit at SLN and does not travel;
row 873 is the PFD's and is correctly in Florida Staging.

Replaces the paragraph rather than appending: a row that says both "still open"
and "answered" is the ROW CONTRADICTS ITSELF case the dashboard flags, and the
reasoning survives in the commit and in docs/G1000.md.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from stock.models import StockItem

COMMIT = "--commit" in sys.argv
NEW = """LOCATION ANSWERED 2026-09-21: it stays at SLN. docs/G1000.md records Scott's
2026-08-29 count of the physical pile - MFD right BUILT, PFD left TO BUILD - so
this unit is in the built MFD in the cockpit here, and row 873 is the PFD's,
correctly bagged for Florida. The row still READS `Unfiled - Machine Shop`
only because nothing has moved it: when MC-T3 was emptied to Florida Staging on
2026-09-20 the sweep selected on `location == MC-T3` and never saw this row.
Closing BO-0020 consumes it and empties the waiting room; do not file it to a
drawer, it is not on a shelf."""

si = StockItem.objects.get(pk=9)
notes = si.notes or ""
paras = notes.split("\n\n")
hit = [i for i, p in enumerate(paras) if p.startswith("STILL OPEN:")]
print("paragraphs: %d, STILL OPEN at %s" % (len(paras), hit))
if len(hit) != 1:
    print("ABORT: expected exactly one STILL OPEN paragraph")
    sys.exit(1)
print("--- was ---\n%s\n--- now ---\n%s" % (paras[hit[0]], NEW))
if not COMMIT:
    print("\nDRY RUN - add --commit")
    sys.exit()

paras[hit[0]] = NEW
want = "\n\n".join(paras)
si.notes = want
si.save()

si = StockItem.objects.get(pk=9)
ok = si.notes == want
print("\nre-read: %s" % ("OK" if ok else "WRITE DID NOT STICK"))
if not ok:
    StockItem.objects.filter(pk=9).update(notes=want)
    print("fell back to queryset update: %s"
          % (StockItem.objects.get(pk=9).notes == want))
print("STILL OPEN present after write: %s" % ("STILL OPEN:" in StockItem.objects.get(pk=9).notes))
