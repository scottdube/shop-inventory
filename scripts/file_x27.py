"""File the X27.168 speedo servos: 7 counted, into B2-R1C4, tagged sim-origin.

Part #276 has existed since a 2023-07-19 Amazon purchase and has NEVER had a
stock row -- a bought thing with no on-hand record, invisible until the box
turned up on the bench.

BENCH STOCK, NOT A BUILD ALLOCATION. Scott, 2026-08-27: "It is really bench
stock. It was purchased originally for the SIM project, but does not currently
have a home in the project. But could still carry that as a tag. Probably not on
the build order, though."

That distinction is the same one florida.py's docstring makes: an allocation
says a part is SPOKEN FOR, which would be false here -- these are available to
anything. So the sim origin goes in metadata plus a tag for UI visibility, and
the stock stays ordinary bench stock.

B3-R5C4 was the only free bin in the motor row and is NOT used: it is large, it
is already earmarked in OPEN.md for the VFD bus caps, and Scott says these fit a
small bin. Taking it would have quietly double-booked the one bin somebody else
is waiting on.

    itq run scripts/file_x27.py            # dry run
    itq run scripts/file_x27.py --commit
"""
import argparse, datetime, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part                                     # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

PART, BIN, QTY = 276, "B2-R1C4", 7
TODAY = datetime.date.today()

DESC = ("X27.168 INSTRUMENT STEPPERS. ECCPP 7-pack, ASIN X002VYTHUN. Bought for "
        "the Cessna sim, held as bench stock. [6 x 2-7/32 x 1-9/16 in, small]")
NOTE = (
 f"TALLIED {TODAY}: Scott counted 7 in hand — a real count, not the 7 on the "
 f"pack label. Box marked 'Speedo Servos' in marker.\n\n"
 "BENCH STOCK. Bought for the Cessna Flight Simulator (BO-0006) but not "
 "allocated to it and deliberately NOT on the build order: it has no home in "
 "the project yet, and an allocation would claim these are spoken for when they "
 "are available to anything. The origin is carried as metadata plus a 'sim' tag "
 "instead — the same distinction florida.py draws between an earmark and an "
 "allocation.\n\n"
 "X27.168 is the standard automotive instrument-cluster stepper AND the standard "
 "part for building analog sim gauges — airspeed, altimeter, VSI. That dual use "
 "is why the sim origin is worth recording even though these are bench stock: "
 "the next person to want an analog gauge should find them.\n\n"
 "Purchased 2023-07-19, Amazon order 113-3379879-0299404, $20.99 for the 7-pack. "
 "No supplier part carries the ASIN and no PO in this system matches it.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

locs = list(StockLocation.objects.filter(name__iexact=BIN))
if len(locs) != 1:
    sys.exit(f"!! {BIN} matched {len(locs)} locations")
loc = locs[0]
p = Part.objects.get(pk=PART)
existing = StockItem.objects.filter(part=p)
print(f"part #{p.pk} {p.name[:56]}")
print(f"  home was: {p.default_location}   stock rows: {existing.count()}")
print(f"  bin {loc.pathstring}")
print(f"  bin says: {(loc.description or '(empty)')[:70]}")
print(f"  qty {QTY}, TALLIED {TODAY}")
if existing.exists():
    sys.exit("!! part already has stock rows — refusing to double-file")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

s = StockItem.objects.create(part=p, location=loc, quantity=QTY, notes=NOTE)
# ORDER MATTERS. .save() writes the whole in-memory row, so a queryset
# .update() done BEFORE it is silently reverted by the stale instance. Do every
# .save()-based write first, then the .update()s, then verify by re-reading.
s.metadata = dict(s.metadata or {}, origin={
    "project": "BO-0006", "project_name": "Cessna Flight Simulator",
    "allocated": False,
    "why": "Bought for the sim; held as bench stock, no home in the project yet.",
    "added": str(TODAY)})
s.save()
s.tags.add("sim")
StockItem.objects.filter(pk=s.pk).update(stocktake_date=TODAY)
fresh = StockItem.objects.get(pk=s.pk)
assert float(fresh.quantity) == QTY, "qty did not stick"
assert fresh.location_id == loc.pk, "location did not stick"
assert fresh.stocktake_date == TODAY, "stocktake did not stick"
assert (fresh.metadata or {}).get("origin", {}).get("project") == "BO-0006", \
    "metadata did not stick"
assert "sim" in [t.name for t in fresh.tags.all()], "tag did not stick"
print(f"\nOK  stock #{fresh.pk} qty={float(fresh.quantity):g} {loc.name} "
      f"tagged sim, origin BO-0006 (not allocated)")

Part.objects.filter(pk=PART).update(default_location=loc)
assert Part.objects.get(pk=PART).default_location_id == loc.pk, "home did not stick"
print(f"OK  default_location -> {loc.pathstring}  (was the bare SLN root)")

StockLocation.objects.filter(pk=loc.pk).update(description=DESC)
assert StockLocation.objects.get(pk=loc.pk).description == DESC, "bin desc did not stick"
print(f"OK  bin described: {DESC[:60]}...")
