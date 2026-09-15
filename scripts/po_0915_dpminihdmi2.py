"""Queue C: Amazon order 111-2294439-2655441 (2026-09-15) -> PO, no new part.

The SECOND order of the same cable in two days. Order 113-0032375-3000231
(PO-0172, 2026-09-13, $12.99) is still "Delayed, not yet shipped"; this one is
the same ASIN B0GZVWP2JF at the same $12.99 and arrives tomorrow. Confirmed the
same ASIN by reading the product href off the order-details page, not by
matching the title — two ZeniKon listings of the same cable would look
identical in text and be different parts.

Whether Scott intends to KEEP both or cancel the delayed one is not something
this run can know, so both POs stand and both stay PLACED. If the delayed one
is cancelled, PO-0172 gets cancelled by hand; nothing here presumes it.

PRICE SOURCE -- the order-details page, per item:

    ZeniKon DP -> Mini HDMI 6.6FT     12.99 x 1
                                      -----
                                      12.99

**The Grand Total on this order is $1.46 and it is not the price.** The page
reads Item(s) Subtotal $12.99, shipping $0.00, tax $0.00, Rewards Points
-$11.53, Grand Total $1.46. Points are a PAYMENT METHOD, not a discount, so the
item price is $12.99 -- exactly the case the standing rule was written for, and
the first time on this install that the gap between the two numbers is
9x rather than a few dollars.

Note this is points, NOT the promotional-discount case on the open decision
item `amazon-promo-discount-vs-item-price`. That item asks what to do when
Amazon shows a real on-listing price reduction; a points redemption is settled
and needs no ruling.

PART: reuses #1198 and supplier part #731, both created by PO-0172 on 09-13.
Nothing new is created here, so there is no category, naming or duplicate call
to make.

PLACED, never received. Arriving 2026-09-16; a human checks it in.
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

ORDER = "111-2294439-2655441"
ISSUE = datetime.date(2026, 9, 15)
ARRIVES = datetime.date(2026, 9, 16)
SUBTOTAL = 12.99

ASIN = "B0GZVWP2JF"
UNIT = "12.99"
QTY = 1

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

# ---------------------------------------------------------------- idempotency
dup_po = PurchaseOrder.objects.filter(
    Q(supplier_reference=ORDER) | Q(reference=ORDER))
if dup_po.exists():
    sys.exit(f"!! PO already exists for {ORDER}: "
             f"{[p.reference for p in dup_po]} — nothing to do")

total = float(UNIT) * QTY
print(f"reconcile: lines sum {total:.2f} vs page subtotal {SUBTOTAL:.2f}")
assert abs(total - SUBTOTAL) < 0.005, "line price does not reconcile — refusing"

# The supplier part MUST already exist: this run creates no part. If it is
# missing, something is wrong with the assumption above and stopping is right.
sp = SupplierPart.objects.filter(supplier=amazon, SKU=ASIN).first()
if sp is None:
    sys.exit(f"!! no supplier part for {ASIN} — expected the one PO-0172 made")
print(f"  reuse sp #{sp.pk} -> part #{sp.part.pk} {sp.part.name}")
print(f"  pack_native={sp.pack_quantity_native}")

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ---------------------------------------------------------------- PO
po = PurchaseOrder(
    supplier=amazon,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=f"Amazon order {ORDER} — DP to mini-HDMI cable (2nd of two)",
    issue_date=ISSUE,
    target_date=ARRIVES,
    status=PurchaseOrderStatus.PLACED.value,
    notes=("Auto-created by the queue C daytime sweep, 08:40 run 2026-09-15. "
           "Ordered 07:49 EDT, after the 02:05 overnight sweep, so this is the "
           "first run that could see it.\n\n"
           "SECOND order of the same cable in two days — PO-0172 "
           "(113-0032375-3000231, 09-13) holds the same ASIN B0GZVWP2JF and is "
           "still 'Delayed, not yet shipped'. Both POs stand; whether the "
           "delayed one is to be cancelled is Scott's call, not an inference "
           "this sweep may make.\n\n"
           "PRICE SOURCE: the order-details page, per item — $12.99. The Grand "
           "Total on this order is $1.46 and is NOT the price: the page reads "
           "subtotal $12.99, shipping $0.00, tax $0.00, Rewards Points -$11.53. "
           "Points are a payment method, not a price reduction.\n\n"
           "PLACED, not received. Arriving 2026-09-16; receive with "
           "receive_po.py when the box is physically checked in."),
)
po.save()
po.refresh_from_db()
assert po.status == PurchaseOrderStatus.PLACED.value, "PO status did not stick"
assert po.supplier_reference == ORDER, "supplier_reference did not stick"
print(f"\nCREATED {po.reference} supplier_ref={po.supplier_reference}")

li = PurchaseOrderLineItem(
    order=po, part=sp, quantity=QTY,
    purchase_price=UNIT, purchase_price_currency="USD",
    notes=("Per-item price from the Amazon order-details page. Grand Total was "
           "$1.46 after $11.53 of Rewards Points; the item is $12.99."))
li.save()
li.refresh_from_db()
assert float(li.purchase_price.amount) == float(UNIT), \
    f"price did not stick: {li.purchase_price}"
print(f"    line: qty {li.quantity} @ {li.purchase_price}")

po.refresh_from_db()
booked = sum(float(l.purchase_price.amount) * float(l.quantity)
             for l in po.lines.all())
print(f"\nDONE  {po.reference}  lines={po.lines.count()}  booked=${booked:.2f}"
      f"  (page subtotal ${SUBTOTAL:.2f})")
assert abs(booked - SUBTOTAL) < 0.005, "booked total drifted from the page"
