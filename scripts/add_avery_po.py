"""Create the Avery 8167 label-stock part + PO for Amazon order 113-7469704-6755457.

Why this order and not a general sweep: it was SKIPPED on 2026-08-18 under the
"label stock is a consumable, not inventoried" decline. Scott reversed that on
08-21 — label stock is now tracked WITH a reorder point, because running out of
it stalls every queued labelling job. pending_decisions.md asks by name for this
order to be created if still in window. Every other Amazon order in the sweep
window already has a PO (checked via supplier_reference).

Price provenance: $11.99 is the **Item(s) Subtotal** read off the order-details
page in Chrome, with qty 1 — NOT the Grand Total. Grand total is cash after
rewards points and gift cards and must never become an item price; that rule
cost this project a $10.99 item recorded as $4.10. Here subtotal and grand total
happen to agree, which is a coincidence of this order, not a licence to use the
latter.

Deliberately does NOT use the vendor order number as `reference`. Doing that is
how three POs got reference_int clamped to int32 max, which broke
generate_reference() — and the "new PO" button in the web UI — for every
subsequent order. Vendor number goes in supplier_reference, full stop.

Leaves the PO PLACED. The box arrived on 08-17, but receiving is a human's job:
it is what creates stock with the right pack conversion. Ordered != received.
"""
import argparse
import datetime
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart      # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from order.status_codes import PurchaseOrderStatus    # noqa: E402
from part.models import Part, PartCategory            # noqa: E402

ORDER = "113-7469704-6755457"
ASIN = "B00004Z5QO"
SKU = f"{ASIN}-AVERY8167"
PRICE = "11.99"
QTY = 1
ISSUE = datetime.date(2026, 8, 16)

NAME = "Label Sheet, Avery 8167 return address, 0.5 x 1.75in"
DESC = ('Printable return address label sheets, 0.5in x 1.75in, white, 80 per sheet, '
        '2000 per pack. Sure Feed. orig: Avery Printable Return Address Labels with '
        'Sure Feed, 0.5" x 1.75", White, 2,000 Blank Mailing Labels (08167)')
KEYWORDS = ("label, labels, label sheet, avery, 8167, return address labels, "
            "address labels, sticker sheet, printable labels, laser labels")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

amazon = Company.objects.filter(name__istartswith="Amazon").first()
if not amazon:
    sys.exit("no Amazon company record")

existing = (PurchaseOrder.objects.filter(supplier_reference=ORDER)
            | PurchaseOrder.objects.filter(reference=ORDER)).distinct().first()
if existing:
    sys.exit(f"PO already exists for {ORDER}: {existing.reference} — nothing to do")

part = Part.objects.filter(name=NAME).first()
cat = PartCategory.objects.filter(name="Consumables").first()

if not a.commit:
    print(f"WOULD create part   : {NAME}")
    print(f"          category  : {cat}")
    print(f"          keywords  : {KEYWORDS}")
    print(f"WOULD create supplier part {SKU} @ {amazon}")
    print(f"WOULD create PO for {ORDER}, PLACED, 1 line, qty {QTY} @ ${PRICE}")
    print(f"          reference : {PurchaseOrder.generate_reference()}")
    sys.exit(0)

if not part:
    part = Part.objects.create(
        name=NAME,
        description=DESC,
        category=cat,
        keywords=KEYWORDS,
        purchaseable=True,
        component=False,
        active=True,
        minimum_stock=1,   # Scott's 08-21 policy: label stock carries a reorder point.
    )
    print(f"created part #{part.pk}")
else:
    print(f"reusing existing part #{part.pk}")

sp = SupplierPart.objects.filter(supplier=amazon, SKU=SKU).first()
if not sp:
    sp = SupplierPart.objects.create(part=part, supplier=amazon, SKU=SKU,
                                     link=f"https://www.amazon.com/dp/{ASIN}")
    print(f"created supplier part #{sp.pk} ({SKU})")

ref = PurchaseOrder.generate_reference()
po = PurchaseOrder.objects.create(
    supplier=amazon,
    reference=ref,
    supplier_reference=ORDER,
    description="Avery 8167 return address label sheets",
    issue_date=ISSUE,
    status=PurchaseOrderStatus.PLACED.value,
    notes=("Created by the overnight enrich job under the 2026-08-21 reversal of the "
           "'label stock is a consumable' decline. Unit price is the Item(s) Subtotal "
           "from the Amazon order-details page (qty 1), NOT the grand total. "
           "Delivered 2026-08-17 but left PLACED — receiving is a human's job."),
)
print(f"created {po.reference} (supplier_ref={po.supplier_reference})")

li = PurchaseOrderLineItem.objects.create(
    order=po, part=sp, quantity=QTY, purchase_price=PRICE,
    purchase_price_currency="USD",
    notes="Price read from order-details page, item subtotal, 2026-08-23.",
)
print(f"created line #{li.pk}: qty {li.quantity} @ {li.purchase_price}")

# Verify by re-reading rather than trusting the writes.
fresh = PurchaseOrder.objects.get(pk=po.pk)
lines = list(fresh.lines.all())
print(f"\nVERIFY: {fresh.reference} status={fresh.get_status_display()} "
      f"supplier_ref={fresh.supplier_reference} lines={len(lines)} "
      f"price={lines[0].purchase_price if lines else None} "
      f"reference_int={fresh.reference_int}")
print(f"part #{part.pk} keywords={Part.objects.get(pk=part.pk).keywords[:60]!r}")
