"""Repair supplier parts whose pack_quantity TEXT and pack_quantity_native disagree.

Found 2026-09-03 while receiving PO-0150..0157. `SupplierPart` keeps the pack in
two fields: `pack_quantity`, a text field a human types and every screen and
audit reads, and `pack_quantity_native`, the Decimal that receiving actually
multiplies by. Only `clean()` derives the second from the first, and `save()`
calls `clean()` — but a queryset `.update(pack_quantity='5')` does not, so the
text changes, the native does not, and NOTHING SAYS SO.

That is the whole explanation for the 2026-08-26 measurement recorded as
"receive_line_item ignores pack_quantity". It does not ignore it:

    stock_quantity = supplier_part.base_quantity(quantity)   # x pack_quantity_native
    purchase_price = line.purchase_price / supplier_part.base_quantity(1)

SP 688 (PATIKIL copper clad) read pack_quantity='5' and native=1, so
base_quantity(1) was 1 and one board was booked at the full $9.49. The pack was
never applied to the field that counts. Today's four supplier parts were created
through save(), had native right, and received correctly with no line repair.

This writes through .save() so clean() runs, then re-reads to prove it stuck.
The text value is treated as the intended one: somebody typed it deliberately
and it is what every screen has been showing.

    itq run scripts/fix_pack_native.py             # dry run
    itq run scripts/fix_pack_native.py --commit
"""
import argparse
import os
import sys
from decimal import Decimal

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart            # noqa: E402
from order.models import PurchaseOrderLineItem     # noqa: E402
from stock.models import StockItem                 # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()


def text_value(sp):
    try:
        return Decimal(str(sp.pack_quantity).strip() or "1")
    except Exception:
        return None


bad = []
for sp in SupplierPart.objects.all():
    tv = text_value(sp)
    if tv is None or tv != sp.pack_quantity_native:
        bad.append((sp, tv))

print(f"{len(bad)} supplier part(s) with pack text != native\n")
for sp, tv in bad:
    lines = PurchaseOrderLineItem.objects.filter(part=sp)
    rows = StockItem.objects.filter(supplier_part=sp)
    print(f"SP {sp.pk}  {sp.SKU}")
    print(f"    part {sp.part.pk} {sp.part.name[:66]}")
    print(f"    text={sp.pack_quantity!r}  native={sp.pack_quantity_native.normalize():g}"
          f"  -> would become {tv if tv is not None else 'UNPARSEABLE'}")
    for ln in lines:
        print(f"    line {ln.pk} on {ln.order.reference} [{ln.order.get_status_display()}] "
              f"qty={float(ln.quantity):g} received={float(ln.received):g} "
              f"price={ln.purchase_price}")
    for r in rows:
        print(f"    stock {r.pk} qty={float(r.quantity):g} price={r.purchase_price} "
              f"@ {r.location.name if r.location else 'UNLOCATED'}")

print("\nAlready-received rows are NOT touched. Stock quantities and prices are "
      "materialised at receive time; nothing re-reads the pack afterwards, so "
      "this only changes how FUTURE receipts against these SKUs behave.")

unparseable = [sp for sp, tv in bad if tv is None]
if unparseable:
    print(f"\n!! {len(unparseable)} unparseable text value(s) — those are skipped "
          "and need a human to say what the pack size is")

if not a.commit:
    sys.exit("\nDRY RUN — add --commit")

fixed, failed = 0, []
for sp, tv in bad:
    if tv is None:
        continue
    sp.save()                      # save() calls clean(), which derives native
    sp.refresh_from_db()
    if sp.pack_quantity_native == tv:
        fixed += 1
        print(f"OK   SP {sp.pk} {sp.SKU}: native now {sp.pack_quantity_native.normalize():g}")
    else:
        failed.append(sp.pk)
        print(f"FAIL SP {sp.pk} {sp.SKU}: native still "
              f"{sp.pack_quantity_native.normalize():g}, wanted {tv}")

# ---- verify by re-running the whole comparison from scratch --------------
remaining = []
for sp in SupplierPart.objects.all():
    tv = text_value(sp)
    if tv is not None and tv != sp.pack_quantity_native:
        remaining.append(sp.pk)

print(f"\nfixed {fixed}; still divergent (parseable): {remaining or 'none'}; "
      f"unparseable left alone: {[s.pk for s in unparseable] or 'none'}")
print("SUCCESS" if not remaining and not failed else "FAILED")
sys.exit(1 if (remaining or failed) else 0)
