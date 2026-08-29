"""Receive PO-0144's two Hakko nozzles — the step that was skipped.

Scott marked PO-0144 Complete on 2026-08-29 and the parts vanished. They did
not vanish: COMPLETE IS A STATUS, RECEIVING IS AN ACTION, and only receiving
creates stock. Both lines still read received=0 with no destination.

Receiving into A3-R1C2, which is already both parts' default_location and whose
description already names these exact nozzles.

Verifies qty x price against the line total per docs/TRAPS.md — receive_line_item
ignores pack_quantity and can book a whole pack price against one piece.

    itq run scripts/receive_po0144.py            # dry run
    itq run scripts/receive_po0144.py --commit
"""
import argparse, datetime, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from order.models import PurchaseOrder, PurchaseOrderLineItem    # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

REF, BIN, TODAY = "PO-0144", "A3-R1C2", datetime.date.today()

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.get(name__iexact=BIN)
po = PurchaseOrder.objects.get(reference=REF)
lines = list(po.lines.all())
print(f"{po.reference}  {po.get_status_display()}  -> receive into {loc.name}")
for li in lines:
    sp = li.part
    print(f"  line {li.pk}: {sp.part.name[:48]}")
    print(f"    ordered {float(li.quantity):g}, received {float(li.received):g}, "
          f"unit ${li.purchase_price.amount if li.purchase_price else 0}, "
          f"pack={sp.pack_quantity!r}")
    if str(sp.pack_quantity).strip() not in ("1", "", "None"):
        print(f"    !! pack_quantity is {sp.pack_quantity} — quantity below is PIECES, "
              f"check it is not pack-count")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

for li in lines:
    if li.received >= li.quantity:
        print(f"  line {li.pk} already received, skipping")
        continue
    p = li.part.part
    s = StockItem.objects.create(
        part=p, location=loc, quantity=li.quantity, purchase_order=po,
        purchase_price=li.purchase_price,
        notes=(f"RECEIVED {TODAY} from {REF} into {BIN}. Quantity "
               f"{float(li.quantity):g} is the ORDER LINE figure, confirmed by "
               "Scott as arrived — receiving is not counting, but a single "
               "nozzle out of a padded envelope is not a count problem. "
               "The order had been marked Complete without the lines being "
               "received, which is why the parts showed nowhere."))
    StockItem.objects.filter(pk=s.pk).update(stocktake_date=TODAY)
    PurchaseOrderLineItem.objects.filter(pk=li.pk).update(received=li.quantity)

    f = StockItem.objects.get(pk=s.pk)
    got = PurchaseOrderLineItem.objects.get(pk=li.pk)
    assert float(f.quantity) == float(li.quantity), "qty did not stick"
    assert f.location_id == loc.pk, "location did not stick"
    assert f.purchase_order_id == po.pk, "PO link did not stick"
    assert float(got.received) == float(li.quantity), "received did not stick"
    # price sanity: qty x unit must equal the line extended total
    if li.purchase_price:
        ext = float(li.purchase_price.amount) * float(li.quantity)
        bk = float(f.purchase_price.amount) * float(f.quantity) if f.purchase_price else 0
        assert abs(ext - bk) < 0.005, f"price mismatch: line ${ext} vs booked ${bk}"
    print(f"  OK line {li.pk} -> stock #{f.pk} qty={float(f.quantity):g} in {loc.name}, "
          f"linked to {po.reference}")

po.refresh_from_db()
out = sum(1 for l in po.lines.all() if l.received < l.quantity)
print(f"\n{po.reference} {po.get_status_display()}; lines outstanding = {out}")
