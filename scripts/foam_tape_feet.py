"""Re-unit the foam tape to FEET, 63 on hand, and earmark 10 ft for Florida.

Scott 2026-08-29: two strips of ~33 ft, three feet already used, "call that the
amount we have in stock", and take 10 ft to Florida.

WHY FEET IS RIGHT HERE AND WAS WRONG FOR SOLDER. Both arguments were made today
and they are not inconsistent. Solder off a roll is consumed in unnoticed
inches, so a running total drifts wrong while looking precise. Weatherstrip is
cut in deliberate lengths for a job — a door takes seven feet and you know you
took it — so the total stays honest. Discrete USE, not discrete PACKAGING, is
what decides the unit.

66 - 3 = 63. That is Scott's figure with the arithmetic shown, NOT a measured
63: the 66 is the pack label and the 3 is his recollection of what went on. The
note says so, so nobody later mistakes it for a tape-measure reading.

pack_quantity 2 -> 66, because one purchased pack is now 66 FEET rather than 2
strips. Leaving it at 2 would make the next receive book 2 ft.

    itq run scripts/foam_tape_feet.py            # dry run
    itq run scripts/foam_tape_feet.py --commit
"""
import argparse, datetime, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from company.models import SupplierPart                          # noqa: E402
from part.models import Part                                     # noqa: E402
from stock.models import StockItem                               # noqa: E402

PART, STOCK, TODAY = 1146, 735, datetime.date.today()
NEW, USED, ONHAND = 66, 3, 63
NAME = "Foam Tape, CR neoprene weatherstrip, 3/8 x 1/4 in (Yotache)"

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

p, s = Part.objects.get(pk=PART), StockItem.objects.get(pk=STOCK)
print(f"#{p.pk} {p.name[:58]}")
print(f"  qty   {float(s.quantity):g} strips -> {ONHAND} ft  ({NEW} new less {USED} used)")
print(f"  units {p.units!r} -> 'ft'")
for sp in SupplierPart.objects.filter(part=p):
    print(f"  supplier {sp.SKU} pack={sp.pack_quantity!r} -> {NEW}")
print(f"  price {s.purchase_price}  (none recorded, so nothing to divide)")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# units first, and VERIFY A CONVERSION rather than just that it saved --
# docs/TRAPS.md: 'M' saves perfectly and means molar.
Part.objects.filter(pk=PART).update(units="ft", name=NAME)
got = Part.objects.get(pk=PART).units
assert got == "ft", f"units did not stick: {got!r}"
from InvenTree.conversion import convert_physical_value          # noqa: E402
probe = float(convert_physical_value("12 in", got))
assert abs(probe - 1.0) < 1e-9, f"conversion broken: 12 in -> {probe} {got}"
print(f"OK  units -> {got!r}   (12 in -> {probe:g} ft, verified)")

NOTE = (
 f"{ONHAND} FT ON HAND, {TODAY}. Scott: two strips of about 33 ft, three feet "
 f"already used. {NEW} - {USED} = {ONHAND}.\n\n"
 "THAT IS ARITHMETIC, NOT A MEASUREMENT. The 66 is the pack label and the 3 is "
 "what Scott recalls using; nobody put a tape on the remainder. Good to a foot, "
 "not to an inch. Recorded this way so a later reader does not mistake it for a "
 "measured figure.\n\n"
 "TRACKED IN FEET, and the reason matters because the opposite call was made "
 "today for solder. Solder off a roll goes in unnoticed inches, so a running "
 "total drifts wrong while looking precise. Weatherstrip is cut in deliberate "
 "lengths for a job — a door takes seven feet and you know you took it — so the "
 "total stays honest. It is discrete USE that decides the unit, not discrete "
 "packaging.\n\n"
 "Two physical strips, not one 66 ft run. A job needing more than 33 ft "
 "continuous cannot be served from this stock however healthy the number looks.\n\n"
 "CR NEOPRENE, NOT EPDM. Shrugs off oil, ozone and weather, so it suits a shop "
 "door — but it takes a compression set: squash it hard and it stays squashed. "
 "Wrong for a lid or hatch that latches shut and must keep sealing; EPDM "
 "recovers better there.\n\n"
 "ADHESIVE-BACKED, SO SURFACE PREP IS THE JOB: clean, dry, above about 10 C. "
 "Cold or dusty and it releases weeks later, which reads as bad tape rather "
 "than bad prep.")

StockItem.objects.filter(pk=STOCK).update(quantity=ONHAND, stocktake_date=TODAY,
                                          notes=NOTE)
Part.objects.filter(pk=PART).update(notes=NOTE)
for sp in SupplierPart.objects.filter(part=p):
    SupplierPart.objects.filter(pk=sp.pk).update(pack_quantity=str(NEW))

f = StockItem.objects.get(pk=STOCK)
assert float(f.quantity) == ONHAND and f.stocktake_date == TODAY, "stock did not stick"
for sp in SupplierPart.objects.filter(part=p):
    assert str(sp.pack_quantity) == str(NEW), "pack_quantity did not stick"
print(f"OK  stock #{f.pk} qty={float(f.quantity):g} ft, pack_quantity {NEW}")
