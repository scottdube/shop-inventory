"""Queue C, 12:40 daytime sweep 2026-11-06: one Amazon order -> one PLACED PO.

  order                 ASIN        qty x pack price  arrives
  113-8469851-5845865   B0GM7T6XWP  2 x  60   6.99   "Arriving Sunday" (11-08)

Placed 2026-11-06, ships to The Villages FL (LRD). Price is the item line on the order-details
page read in Chrome 2026-11-06 12:4x: $6.99 each, subtotal $13.98, tax $0.98, gift card -$12.69,
grand total $2.27 (the email's Grand Total is NOT the price -- gift card applied).
Sold by MTCELL. Listing: "MTCELL 60 Pcs 7 Pin Female Header 2.54mm Single Row Straight
Connector" -> pack 60, counted in 1x7 sockets.

Part mapping: #1183 'Header Socket 1x7 Female 0.1in' is the expected reuse; the dry run prints
every candidate so a second 1x7 female row would show before commit.

Dry run by default; --commit writes. PLACED, never received.
"""
import argparse
import datetime
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402
from part.models import Part  # noqa: E402
from plugins.notes_compat import note_set, note_text  # noqa: E402

RUN = "12:40 daytime sweep 2026-11-06"
ORDER = "113-8469851-5845865"
ASIN = "B0GM7T6XWP"
QTY, PRICE, PACK = 2, "6.99", "60"
ISSUE = datetime.date(2026, 11, 6)
ARRIVE = datetime.date(2026, 11, 8)
NAME = "Header Socket 1x7 Female 0.1in"
SP_DESC = "MTCELL 1x7 female header 2.54mm straight, 60 pcs"
REUSE = 1183  # confirmed against the dry run's candidate list before --commit

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")
ref = Part.objects.get(pk=REUSE)
print(f"REUSE #{ref.pk} active={ref.active} {ref.name!r} cat={ref.category} | {ref.description[:100]!r}")

cands = Part.objects.filter(
    (Q(name__icontains="1x7") | Q(description__icontains="1x7") | Q(name__icontains="7 pin")
     | Q(description__icontains="7 pin") | Q(name__icontains="7-pin") | Q(description__icontains="7-pin")
     | Q(name__icontains="1 x 7") | Q(description__icontains="1 x 7") | Q(name__icontains="7P")
     | Q(description__icontains=ASIN) | Q(IPN__icontains=ASIN) | Q(description__icontains="MTCELL"))
    & (Q(name__icontains="female") | Q(description__icontains="female")
       | Q(name__icontains="socket") | Q(description__icontains="socket")))
for c in cands:
    print(f"  cand #{c.pk} active={c.active} {c.name!r} | {c.description[:90]!r}")
for s in SupplierPart.objects.filter(part_id=REUSE):
    print(f"  existing sp #{s.pk} {s.supplier} {s.SKU!r} pack={s.pack_quantity}/{s.pack_quantity_native}")
sp_hits = SupplierPart.objects.filter(SKU__iexact=ASIN)
print(f"  sp with SKU {ASIN}: {[(s.pk, s.part_id) for s in sp_hits]}")
dup = PurchaseOrder.objects.filter(Q(supplier_reference=ORDER) | Q(reference=ORDER))
print(f"{ORDER}: existing={[(p.reference, p.lines.count()) for p in dup]}")

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --commit")

assert ref.active and ref.name == NAME, "reuse target changed; re-read the dry run"
sp = SupplierPart.objects.filter(supplier=amazon, SKU__iexact=ASIN).first()
if sp is None:
    sp = SupplierPart(supplier=amazon, part=ref, SKU=ASIN,
                      link=f"https://www.amazon.com/dp/{ASIN}", description=SP_DESC)
    sp.pack_quantity = PACK
    sp.save()  # .save(), never .update(): only pack_quantity_native is read at receive
    sp.refresh_from_db()
    assert sp.SKU == ASIN and sp.part_id == ref.pk, "sp did not stick"
    assert float(sp.pack_quantity_native) == float(PACK), sp.pack_quantity_native
    print(f"CREATED sp #{sp.pk} {ASIN} -> part #{ref.pk} pack native={sp.pack_quantity_native}")

if dup.exists():
    assert dup.count() == 1
    po = dup.first()
    if po.lines.count():
        raise SystemExit(f"SKIP {ORDER}: {po.reference} already has lines")
    print(f"RESUMING {po.reference} (0 lines)")
else:
    po = PurchaseOrder(supplier=amazon, reference=PurchaseOrder.generate_reference(),
                       supplier_reference=ORDER,
                       description=f"Amazon order {ORDER} — {SP_DESC} x{QTY} (to The Villages FL)",
                       issue_date=ISSUE, target_date=ARRIVE,
                       status=PurchaseOrderStatus.PLACED.value)
    po.save()
    po.refresh_from_db()
assert po.supplier_id == amazon.pk and po.supplier_reference == ORDER
assert po.status == PurchaseOrderStatus.PLACED.value and po.reference != ORDER
note_set(po, f"Auto-created by the queue C daytime sweep, {RUN}.\n\nShips to The Villages FL (LRD).\n\n"
             f"Line price read from the Amazon order-details page: 2 x $6.99, subtotal $13.98, tax "
             f"$0.98, gift card -$12.69, grand total $2.27.\n\nLine is in packs of {PACK} at the pack "
             f"price; supplier part {ASIN} carries pack_quantity {PACK}, so receive_po.py books "
             f"sockets.\n\nPLACED, not received.")
assert note_text(po).startswith("Auto-created"), "PO note did not stick"
li = PurchaseOrderLineItem(order=po, part=sp, quantity=QTY,
                           purchase_price=PRICE, purchase_price_currency="USD")
li.save()
li.refresh_from_db()
assert float(li.quantity) == QTY and float(li.purchase_price.amount) == float(PRICE)
po.refresh_from_db()
print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
      f"target={po.target_date} lines={po.lines.count()} ({QTY} x sp #{sp.pk} @ {PRICE})")
