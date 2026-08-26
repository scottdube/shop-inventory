"""File the 2 nylon sleeve bearings, rename for the label, record the real order.

Scott 2026-08-26: "I have these 2 in my hand", then "label".

RENAMED. "Light Duty Dry-Running Nylon Sleeve Bearing for 3/8" Shaft Diameter
and 1/2" Housing ID, 3/8" Long" is 97 characters. A sleeve bearing has THREE
numbers that all matter -- shaft, housing, length -- and on 62 mm tape that name
truncates around the first one. The new name carries all three in 32 characters.

THE MCMASTER PAGE GIVES AN ORDER REFERENCE THE PO DOES NOT: "2 each ordered on
January 31, 2022, 0131SDUBE". PO-0130 records issue_date 2022-02-01 and
supplier_reference 72218976.

So the PO date is ONE DAY LATER than the order date, and the two references are
different things -- 0131SDUBE is McMaster's order number (date + customer), and
72218976 is presumably the invoice or shipment. Recorded because the whole
2022 project-cluster reconstruction earlier today was built on PO issue dates.
It does not change any conclusion, but "the PO date is not the order date" is
the kind of half-truth that eventually costs an hour.

COUNT IS 2, WHICH THE BOOKS ALREADY SAID. That is the stocktake() no-op case:
the quantity does not change, so the method writes nothing and the row keeps
reading never-counted. Date set directly.
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
            print(f"  locked on {what}, retry {i+1} in {0.5*(2**i):.1f}s")
            time.sleep(0.5 * (2 ** i))

p = Part.objects.get(pk=1041)
si = StockItem.objects.filter(part=p).first()
binloc = StockLocation.objects.get(pk=587)
NEW = "Nylon Sleeve Bearing 3/8x1/2x3/8"
print(f"[{p.pk}] {p.name}  ({len(p.name)} chars)")
print(f"  -> {NEW}  ({len(NEW)} chars)")
print(f"  qty={si.quantity:g} loc={si.location or 'UNLOCATED'} -> {binloc.name}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

def move():
    si.location = binloc
    si.save()
retry(move, "location")

retry(lambda: StockItem.objects.filter(pk=si.pk).update(
    stocktake_date=datetime.date(2026, 8, 26),
    notes=("TALLIED 2026-08-26. Scott counted 2, in hand.\n\n"
           "SAME NUMBER THE BOOKS HELD, and that is why it needed doing: the 2 "
           "was PO-0130's line quantity from 2022, what was bought rather than "
           "what survived four years. It is now a count.\n\n"
           "This is the case stocktake() silently drops — the quantity does not "
           "change, so the method writes nothing and the row keeps reading "
           "never-counted. The date was set directly.\n\n"
           "FOUND. Read location=NULL since the McMaster import; another whose "
           "'unknown location' meant the record never knew.")), "stock notes")

def rename():
    p.name = NEW
    p.save()
retry(rename, "rename")

retry(lambda: Part.objects.filter(pk=1041).update(
    description="Dry-running nylon sleeve bearing (plain bushing), 3/8 in shaft, "
                "1/2 in housing ID, 3/8 in long. Light duty, runs unlubricated. "
                "McMaster 6389K349.",
    notes=(Part.objects.get(pk=1041).notes or "").rstrip() +
    "\n\nRENAMED 2026-08-26 for the label. The McMaster name is 97 characters "
    "and a sleeve bearing has THREE numbers that all matter — shaft, housing, "
    "length. On 62 mm tape the vendor name truncates around the first one. All "
    "three now fit in 32 characters.\n\n"
    "REAL ORDER REFERENCE, off the McMaster page: **2 each ordered 2022-01-31, "
    "order 0131SDUBE**. PO-0130 records issue_date 2022-02-01 and "
    "supplier_reference 72218976 — so the PO date is a DAY LATER than the order "
    "date and the two references are different things. Worth knowing: the 2022 "
    "project cluster was reconstructed from PO issue dates. No conclusion "
    "changes, but the PO date is not the order date.\n\n"
    "DRY-RUNNING means it is designed to run WITHOUT lubricant. Oiling a nylon "
    "bushing does not help it and can swell the nylon."),
    "part notes")

si.refresh_from_db(); p.refresh_from_db()
print(f"\n[{p.pk}] {p.name}")
print(f"  qty={si.quantity:g} @ {si.location.name} stocktake={si.stocktake_date}")
print(f"unlocated rows with stock: "
      f"{StockItem.objects.filter(location__isnull=True, quantity__gt=0).count()}")
