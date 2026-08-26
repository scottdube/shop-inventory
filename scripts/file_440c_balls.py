"""Count, file and rename the 440C balls. Retries on SQLite write locks.

Scott 2026-08-26: "I have these count 99", then "label".

WRITE LOCK. The first attempt died with `database is locked` -- InvenTree runs
on SQLite and something else held a write. Nothing landed: quantity was still
100 and the row still unlocated, so the failure was clean. That is worth
knowing, because a HALF-applied stock change would be far worse than a failed
one, and the instinct on seeing a traceback is to re-run blindly.

**Check state before retrying a write that threw.** Here it was safe. It will
not always be.

RENAMED FOR THE LABEL. "Hardened Bearing-Quality 440C Stainless Steel Ball,
3/16" Diameter" is 64 characters and truncates on 62 mm tape -- one of the 90
McMaster-imported names measured earlier today. The diameter is the whole
identity of a ball bearing and it sits at the very end.

GRADE 100 is on the vendor page and now in the name. It is a SPHERICITY AND
SIZE tolerance -- 100 millionths of an inch -- not a hardness, despite sitting
next to "Hardened" in the vendor's own title. Uncontrolled balls are not a
substitute in anything that has to run true.
"""
import argparse, os, sys, time, django, datetime

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.utils import OperationalError
from django.contrib.auth import get_user_model
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
            wait = 0.5 * (2 ** i)
            print(f"  locked on {what}, retry {i+1}/{tries-1} in {wait:.1f}s")
            time.sleep(wait)

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
p = Part.objects.get(pk=1005)
si = StockItem.objects.filter(part=p).first()
binloc = StockLocation.objects.get(pk=587)
NEW = "440C Stainless Ball, 3/16 in, Gr100"

print(f"[{p.pk}] {p.name}  ({len(p.name)} chars)")
print(f"  -> {NEW}  ({len(NEW)} chars)")
print(f"  qty={si.quantity:g} -> 99, loc={si.location or 'UNLOCATED'} -> {binloc.name}")

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

if float(si.quantity) == 100:
    retry(lambda: si.take_stock(1, user,
          notes="Count corrected 100 -> 99 by Scott, 2026-08-26."), "take_stock")
si.refresh_from_db()

def move():
    si.location = binloc
    si.save()
retry(move, "location")

retry(lambda: StockItem.objects.filter(pk=si.pk).update(
    stocktake_date=datetime.date(2026, 8, 26),
    notes=("TALLIED 2026-08-26. Scott counted 99 in hand.\n\n"
           "Was 100, which was PO-0122's line quantity from 2023-01-09 — what "
           "was BOUGHT, not what is left. One has gone in three years and "
           "nobody knows into what.\n\n"
           "FOUND. This row read location=NULL since the McMaster import and is "
           "another whose 'unknown location' meant the record never knew rather "
           "than the shop not knowing. Filed to Bearings & Motion, which it "
           "already named as default_location.\n\n"
           "GRADE 100 is a SPHERICITY AND SIZE tolerance — 100 millionths of an "
           "inch — not a hardness, despite sitting beside 'Hardened' in the "
           "vendor's title. Uncontrolled balls are not a substitute where "
           "something has to run true.")), "notes")

def rename():
    p.name = NEW
    p.save()
retry(rename, "rename")
retry(lambda: Part.objects.filter(pk=1005).update(
    description="Hardened 440C stainless steel ball, 3/16 in diameter, Grade 100 "
                "(sphericity/size tolerance of 100 millionths of an inch). "
                "Ultra-wear-resistant. McMaster 9529K13, packs of 100.",
    notes=(Part.objects.get(pk=1005).notes or "").rstrip() +
    "\n\nRENAMED 2026-08-26 for the label. The McMaster name — 'Hardened "
    "Bearing-Quality 440C Stainless Steel Ball, 3/16\" Diameter' — is 64 "
    "characters and truncates on 62 mm tape, dropping the DIAMETER, which is "
    "the entire identity of a ball. One of the 90 imported names measured "
    "today with the same problem. Full vendor text is in the description."),
    "desc")

si.refresh_from_db(); p.refresh_from_db()
print(f"\n[{p.pk}] {p.name}")
print(f"  qty={si.quantity:g} @ {si.location.name} stocktake={si.stocktake_date}")
print(f"unlocated rows with stock: "
      f"{StockItem.objects.filter(location__isnull=True, quantity__gt=0).count()}")
