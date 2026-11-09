"""Set pack_quantity=400 on the two Amazon zip-bag supplier parts (559 JINYONBAG-2x3,
560 Aubeco-3x4) so PO-0274 receives 400 BAGS at the per-bag price, not 1 bag at $7.99.

This settles `zip-bag-pack-quantity-400-vs-1` for these two in the direction CLAUDE.md
has mandated since 2026-09-01: stock counts PIECES, the supplier part carries the pack.
The 2026-08-17 note ("pack_quantity left at 1 to match the rest of the catalog") predates
that ruling, and the existing stock rows 283/284 already count 400 bags each, so a pack
of 1 contradicts the shelf. Historical purchase_price on 283/284 is printed, not changed. The $0.02 per-bag price
breaks become per-PACK ($7.99 / $9.99) because InvenTree prices the supplier-part unit.

Writes through .save() so clean() derives pack_quantity_native (TRAPS: .update() leaves
native at 1 and receiving multiplies by native). Re-reads to prove it.
    itq run scripts/zipbag_pack_400_1109.py            # dry run
    itq run scripts/zipbag_pack_400_1109.py --commit
"""
import os, sys
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django; django.setup()
from django.db import transaction
from company.models import SupplierPart
from stock.models import StockItem

COMMIT = "--commit" in sys.argv
PER_PACK = {559: "7.99", 560: "9.99"}   # PO-0274 / 2026-08-17 listing prices, per 400-bag pack
class DryRun(Exception): pass

for pk in (283, 284):
    s = StockItem.objects.get(pk=pk)
    print(f"stock {pk} qty={s.quantity} purchase_price={s.purchase_price} (historical, untouched)")
try:
    with transaction.atomic():
        for pk in (559, 560):
            sp = SupplierPart.objects.get(pk=pk)
            print(f"SP {pk} {sp.SKU}: pack_quantity={sp.pack_quantity!r} native={sp.pack_quantity_native}",
                  "price_breaks=", [(str(b.quantity), str(b.price)) for b in sp.pricebreaks.all()])
            sp.pack_quantity = "400"
            sp.save()
            # price breaks are per supplier-part UNIT = per pack once the pack is 400
            for b in sp.pricebreaks.all():
                b.price = PER_PACK[pk]
                b.save()
            sp = SupplierPart.objects.get(pk=pk)
            assert sp.pack_quantity_native == 400, sp.pack_quantity_native
            print(f"   -> pack_quantity={sp.pack_quantity!r} native={sp.pack_quantity_native}",
                  "price_breaks=", [(str(b.quantity), str(b.price)) for b in sp.pricebreaks.all()])
        if not COMMIT:
            raise DryRun
except DryRun:
    print("DRY RUN - rolled back. Re-run with --commit.")
else:
    print("COMMITTED")
