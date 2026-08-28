"""File the two VFD DC bus caps into A3-R7C5. Small bin, not the large one.

Parked since 2026-08-23 ("we'll handle it tomorrow"). B3-R5C4 was the earlier
recommendation; Scott 2026-08-28: "Those caps will also fit in a smaller drawer,
so I think we should rehome those to somewhere smaller."

WHY A3-R7 AND NOT A3-R8, the capacitor row. A3-R8 is signal-level electrolytics
-- 1uF to 100uF at 25-50V, 5x11mm bodies. These are 820uF at 400V. Filing a
lethal DC bus cap in with parts you grab bare-handed is a category error that
the bin description would not fix. A3-R7 is the MAINS-SIDE row (input fuses at
C3, barrier terminal blocks at C4), C4 already holds this same VFD's terminal
blocks, and C5 is the free bin next to it.

Write order per docs/TRAPS.md: .save()-based writes first, .update()s second,
re-read and assert last. A .save() after an .update() silently reverts it.

    itq run scripts/file_bus_caps.py            # dry run
    itq run scripts/file_bus_caps.py --commit
"""
import argparse, datetime, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part                                     # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

PART, BIN, QTY = 1076, "A3-R7C5", 2
TODAY = datetime.date.today()

BINDESC = ("HIGH-VOLTAGE DC BUS CAPS — salvaged 400V electrolytics. Kept OUT of "
           "the A3-R8 capacitor row on purpose: that row is 25-50V signal parts "
           "you pick up bare-handed, and these hold a lethal charge. Neighbours "
           "the mains-side fuses (C3) and this VFD's own terminal blocks (C4). "
           "[6 x 2-7/32 x 1-9/16 in, small]")

NOTE = (
 f"TALLIED {TODAY}: 2 in hand. Both individually tested by Scott 2026-08-23 with "
 "the LCR-P1, which is why the count is certain — each one was handled.\n\n"
 "MEASURED, both good:\n"
 "  cap A   761 uF   ESR 0.21 ohm   V-loss 0.8%\n"
 "  cap B   737 uF   ESR 0.21 ohm   V-loss 0.8%\n"
 "Nominal is 820 uF, so these read 93% and 90% of rated — inside the -20% "
 "tolerance these parts ship with, and the matched ESR and loss figures say "
 "aged-but-healthy rather than degraded. They are usable.\n\n"
 "DANGER, and it does not expire with the drive: a DC bus cap holds a lethal "
 "charge long after power is removed, and a drive that died may never have bled "
 "down. METER ACROSS THEM FIRST and confirm near zero before handling.\n\n"
 "Salvaged from the VFD that failed with all six heatsink IGBTs shorted. The "
 "fan (#1078, B3-R5C3) and both terminal blocks (#1079/#1081, A3-R7C4) came off "
 "the same board and are already filed; the heatsink (#1077) is still pending a "
 "hole-spacing measurement.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

locs = list(StockLocation.objects.filter(name__iexact=BIN))
if len(locs) != 1:
    sys.exit(f"!! {BIN} matched {len(locs)} locations")
loc, p = locs[0], Part.objects.get(pk=PART)
print(f"part #{p.pk} {p.name}")
print(f"  home was {p.default_location}, stock rows {StockItem.objects.filter(part=p).count()}")
print(f"  -> {loc.pathstring}, qty {QTY}, TALLIED {TODAY}")
print(f"  bin was: {(loc.description or '')[:64]}")
if StockItem.objects.filter(part=p).exists():
    sys.exit("!! already has stock rows — refusing to double-file")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

s = StockItem.objects.create(part=p, location=loc, quantity=QTY, notes=NOTE)
StockItem.objects.filter(pk=s.pk).update(stocktake_date=TODAY)
Part.objects.filter(pk=PART).update(default_location=loc)
StockLocation.objects.filter(pk=loc.pk).update(description=BINDESC)

f = StockItem.objects.get(pk=s.pk)
assert float(f.quantity) == QTY and f.location_id == loc.pk, "row did not stick"
assert f.stocktake_date == TODAY, f"stocktake did not stick: {f.stocktake_date}"
assert Part.objects.get(pk=PART).default_location_id == loc.pk, "home did not stick"
assert StockLocation.objects.get(pk=loc.pk).description == BINDESC, "bin desc did not stick"
print(f"\nOK  stock #{f.pk} qty={float(f.quantity):g} in {loc.name}, "
      f"stocktake {f.stocktake_date}")
print(f"OK  #{PART} home -> {loc.pathstring}")
print(f"OK  bin described as high-voltage")
