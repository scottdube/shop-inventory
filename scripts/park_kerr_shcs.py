"""Park the Kerr 1/4-20 x 1 box at B2-R4C7. A SECOND row of #955, not a merge.

Scott 2026-08-26: "45 is count", "b2r4c7 is a temp home".

That also resolves the stray "count 45" from earlier, which was assigned to the
M3 screws on inference and turned out to belong here. It was the Kerr box all
along.

BOX: Kerr Lakeside 25C100KCSIX, "1/4-20 X 1 Hex Socket Head Cap Screw, ASME
B18.3, Alloy Steel", QTY 50, made in USA, lot P-36416-10810020. Scott counted
45, so five have gone.

NOT MERGED INTO #955's EXISTING ROW, deliberately. The house rule is that buying
more of something merges -- but B2-R3 is FULL, all eight cells, and the 1/4-20
family already has a homeless length (#959, the 1-1/4 in) sitting at cabinet
level. Adding 45 to the 40 in B2-R3C7 would put 85 screws into a row that has
already failed, and would hide the fact that the stock is in two places.

Two rows of one part in two locations is allowed: the invariant is one row per
part per LOCATION. It also happens to be true, which is the better argument.

DEFAULT_LOCATION IS NOT CHANGED. B2-R4C7 is a TEMP home and the policy is
explicit that default_location is where a spare goes home -- never a staging
area. The part keeps pointing at its real cell; only this row sits elsewhere,
and its note says why and for how long.
"""
import argparse, os, sys, time, django, datetime

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.utils import OperationalError
from part.models import Part
from stock.models import StockItem, StockLocation

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

def retry(fn, what, tries=6):
    for i in range(tries):
        try:
            return fn()
        except OperationalError as e:
            if "locked" not in str(e).lower() or i == tries - 1:
                raise
            print(f"  locked on {what}, retry {i+1}")
            time.sleep(0.5 * (2 ** i))

p = Part.objects.get(pk=955)
cell = StockLocation.objects.get(name="B2-R4C7")
existing = StockItem.objects.filter(part=p)
print(f"[{p.pk}] {p.name[:64]}")
print(f"  default_location: {p.default_location}")
for s in existing:
    print(f"  existing row [{s.pk}] {s.quantity:g} @ {s.location.name if s.location else '-'}")
print(f"  parking 45 at {cell.pathstring}  ({StockItem.objects.filter(location=cell).count()} rows there now)")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

row = StockItem.objects.filter(part=p, location=cell).first()
if not row:
    row = retry(lambda: StockItem.objects.create(part=p, location=cell, quantity=45), "create")
    print(f"  created row [{row.pk}]")

retry(lambda: StockItem.objects.filter(pk=row.pk).update(
    stocktake_date=datetime.date(2026, 8, 26),
    notes=("TALLIED 2026-08-26. Scott counted 45.\n\n"
           "**TEMP HOME.** B2-R4C7 is a parking cell, not this part's home, and "
           "it is here because B2-R3 is FULL — all eight cells — and the 1/4-20 "
           "family already has a homeless length (#959, 1-1/4 in) at cabinet "
           "level. See OPEN.md: that row needs reordering before anything is "
           "filed into it properly.\n\n"
           "SECOND ROW OF THIS PART ON PURPOSE, not merged into the 40 at "
           "B2-R3C7. Merging would report 85 in a cell that cannot hold them and "
           "would hide that the stock is in two places. One row per part per "
           "LOCATION is the invariant, and two locations is the truth.\n\n"
           "default_location is UNCHANGED and still points at the real home. A "
           "temp cell must never become a default_location — that is how a "
           "staging area turns permanent.\n\n"
           "BOX: Kerr Lakeside Inc, 25C100KCSIX, '1/4-20 X 1 Hex Socket Head Cap "
           "Screw, ASME B18.3, Alloy Steel', QTY 50, MADE IN USA, lot "
           "P-36416-10810020. Five have gone. Different vendor from the "
           "McMaster stock in B2-R3C7 — same spec, both black-oxide alloy steel, "
           "confirmed by Scott looking at them.\n\n"
           "This is also where the stray 'count 45' from earlier belongs. It was "
           "assigned to the M3 screws by inference and was wrong; the M3s are "
           "100.")), "notes")

row.refresh_from_db(); p.refresh_from_db()
print("\nverify:")
tot = 0
for s in StockItem.objects.filter(part=p):
    tot += float(s.quantity)
    print(f"  [{s.pk}] {s.quantity:g} @ {s.location.name}  stocktake={s.stocktake_date}")
print(f"  total across locations: {tot:g}")
print(f"  default_location still: {p.default_location.name if p.default_location else 'NONE'}")
