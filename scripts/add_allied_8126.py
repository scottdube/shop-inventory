"""Allied 8126 22AWG 4-conductor into B-01 — the last of the wire.

Not on any purchase order and not in the Amazon order history: Allied Wire and
Cable is a distributor, so this almost certainly did not come through the swept
vendors at all. Provenance recorded as UNKNOWN rather than guessed.

~10 ft is Scott's eyeball, 2026-08-24. [ESTIMATE], no stocktake_date.

The jacket carries a SEQUENTIAL FOOTAGE MARK (#4626 FT.). If the other end's
mark ever turns up, subtracting the two gives the exact length for free — no
weighing, no measuring, nothing cut. Recorded because it is the cheapest route
to a real number and it is invisible unless somebody knows to look.
"""
import argparse, os, sys
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part                       # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

NAME = "Multi-Conductor Cable 22 AWG 4-core, grey CMG (Allied 8126)"
DESC = ("22 AWG 4-conductor CMG communications cable, grey jacket. Allied Wire "
        "and Cable 8126, UL E171197. SIGNAL cable — data, sensor and control "
        "runs. Looks like ordinary grey wire but is NOT interchangeable with "
        "the 20/2 power cable in this bin.")
NOTES = """## As found

Jacket print, read 2026-08-24:

> `#4626 FT.  ALLIED WIRE AND CABLE  8126  E171197-01  22AWG 4C (UL) CMG`

**`#4626 FT.` is a sequential footage mark, not the length of this piece.** If
the mark at the OTHER end is ever read, subtracting the two gives the exact
length — free, exact, nothing cut and nothing weighed. Cheapest route to a real
number here, and invisible unless you know to look for it.

## Provenance — UNKNOWN

On no purchase order, and absent from the Amazon order history. Allied Wire and
Cable is a distributor, so this likely never passed through any swept vendor.
Possibly salvage or a leftover from a job. Recorded as unknown rather than
attributed to a guess.

## Quantity

~10 ft, Scott's eyeball 2026-08-24. Nothing measured or weighed.
"""

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

assert len(DESC) <= 250, len(DESC)
loc = StockLocation.objects.get(name="B-01")
tmpl = Part.objects.get(pk=1091)
if Part.objects.filter(name__iexact=NAME).exists():
    print("!! duplicate"); raise SystemExit(1)
print(f"{NAME}\n  -> ~10 ft @ {loc.pathstring}")
if not a.commit:
    print("DRY RUN"); raise SystemExit

p = Part.objects.create(name=NAME, description=DESC, notes=NOTES,
                        category=tmpl.category, default_location=loc,
                        active=True, units="ft",
                        keywords=("multi-conductor, multicore, 22awg, 4 core, 4c, "
                                  "CMG, communications cable, signal cable, grey, "
                                  "allied wire and cable, 8126, E171197"))
f = Part.objects.get(pk=p.pk)
assert f.units == "ft" and f.default_location_id == loc.pk
si = StockItem.objects.create(
    part=f, location=loc, quantity=10,
    notes=("[ESTIMATE] ~10 ft, Scott's eyeball 2026-08-24. Nothing measured or "
           "weighed, so no stocktake_date. EXACT length is available for free if "
           "the footage mark at the other end is read — the jacket carries "
           "sequential marks and this end reads #4626 FT."))
c = StockItem.objects.get(pk=si.pk)
assert float(c.quantity) == 10 and c.stocktake_date is None
print(f"OK  part #{f.pk}, stock #{c.pk}, 10 ft @ B-01")
