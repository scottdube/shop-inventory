"""Re-stock the Chip Quik low-temp solder as 59 STICKS, not 1 container.

Scott 2026-08-29: "its not a roll its 6.5 in sticks so its easy to inventory."
Counted 59.

WHY THE UNIT CHANGES. The earlier reasoning against length-tracking was about a
CONTINUOUS consumable -- solder off a roll is used in unnoticed inches and any
running total drifts wrong while looking precise. Sticks are discrete and
countable, so none of that applies: you take eight sticks to Florida and count
what is left. No `units` field is set, because a plain count needs none and that
also sidesteps the pint trap on part #790 (lowercase 'm', because pint reads 'M'
as molar).

PRICE MUST BE DIVIDED IN THE SAME BREATH. StockItem.purchase_price is PER UNIT.
The row holds $57.46 against qty 1; changing the quantity to 59 without touching
it values the tube at $3,390. This is docs/TRAPS.md's pack-quantity trap arriving
by a different road -- there it was a receive, here it is a re-count.

SupplierPart.pack_quantity goes to 59 too, so the NEXT receive of this SKU
divides correctly rather than repeating the error.

    itq run scripts/restock_solder_sticks.py            # dry run
    itq run scripts/restock_solder_sticks.py --commit
"""
import argparse, datetime, os, sys, django
from decimal import Decimal, ROUND_HALF_UP

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from company.models import SupplierPart                          # noqa: E402
from part.models import Part                                     # noqa: E402
from stock.models import StockItem                               # noqa: E402

PART, STOCK, STICKS, TODAY = 1107, 734, 59, datetime.date.today()

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

s = StockItem.objects.get(pk=STOCK)
p = Part.objects.get(pk=PART)
old_qty = float(s.quantity)
old_unit = Decimal(str(s.purchase_price.amount)) if s.purchase_price else Decimal("0")
total = old_unit * Decimal(str(old_qty))
new_unit = (total / Decimal(STICKS)).quantize(Decimal("0.0001"), ROUND_HALF_UP)

print(f"stock #{s.pk}  {s.part.name[:48]}  at {s.location.name}")
print(f"  qty   {old_qty:g} container   -> {STICKS} sticks")
print(f"  price ${old_unit} each        -> ${new_unit} each")
print(f"  row total ${total} -> ${new_unit * Decimal(STICKS)}   (must not move)")
for sp in SupplierPart.objects.filter(part=p):
    print(f"  supplier {sp.SKU} pack={sp.pack_quantity!r} -> {STICKS}")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

NOTE = (
 f"COUNTED {TODAY}: 59 sticks, counted by Scott. Re-stocked from '1 container' "
 "to 59 pieces because the product is 6.5 in STICKS, not a roll — discrete and "
 "countable, so the quantity can track real use.\n\n"
 "PRICE WAS DIVIDED AT THE SAME TIME. purchase_price is per unit, so raising the "
 f"quantity from 1 to 59 without it would have valued this tube at "
 f"${old_unit * Decimal(STICKS)} instead of ${total}. Per-stick is ${new_unit}.\n\n"
 "32 ft total per the listing; 59 x 6.5 in is 383.5 in, which is 31.96 ft — the "
 "count and the listing agree, so 59 is corroborated rather than just asserted.\n\n"
 "Earmarked for Florida: see scripts/florida.py. With sticks the earmark can say "
 "'N of 59' and the split is simply handing over that many, with no measuring "
 "and no second spool.")

StockItem.objects.filter(pk=STOCK).update(quantity=STICKS, purchase_price=new_unit,
                                          stocktake_date=TODAY)
cur = StockItem.objects.get(pk=STOCK).notes or ""
StockItem.objects.filter(pk=STOCK).update(notes=NOTE + "\n\n" + cur)
for sp in SupplierPart.objects.filter(part=p):
    SupplierPart.objects.filter(pk=sp.pk).update(pack_quantity=str(STICKS))

f = StockItem.objects.get(pk=STOCK)
assert float(f.quantity) == STICKS, "qty did not stick"
assert f.stocktake_date == TODAY, "stocktake did not stick"
booked = Decimal(str(f.purchase_price.amount)) * Decimal(str(f.quantity))
assert abs(booked - total) < Decimal("0.01"), f"value moved: ${total} -> ${booked}"
for sp in SupplierPart.objects.filter(part=p):
    assert str(sp.pack_quantity) == str(STICKS), "pack_quantity did not stick"
print(f"\nOK  qty={float(f.quantity):g} sticks, ${f.purchase_price.amount}/stick, "
      f"row value ${booked} (unchanged), counted {f.stocktake_date}")
