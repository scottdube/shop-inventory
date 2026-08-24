"""Queue C, daytime sweep 12:46 2026-08-24: one new Amazon order.

Window 2026-08-23 -> today. Three Amazon order confirmations were in window;
two (113-6309387-8181062, 113-3993148-7168211) already exist as PO-0137/PO-0138
from the 08:12 run, confirmed via po_check.py. Only this one is new.

113-5011479-9313006 is a REORDER of the SHT31-D 4-pack already bought on
113-1351848-4611464 (PO-0028) four days earlier -- same ASIN B0B5TN8LZB, same
$16.99. So no new part should be created; if this script reports creating one,
the ASIN did not match and that is the thing to look at.

Price read from the order-details page in Chrome, not the email: Item(s)
Subtotal $16.99, Shipping $0.00, tax $0.00, Grand Total $16.99 -- no rewards
points on this one, so email and page happen to agree. That agreement is a
coincidence, not a licence to trust the email next time.

Reference discipline: visible reference from generate_reference(); the vendor
order number goes ONLY in supplier_reference.

PLACED, not received. No stock created.
"""
import argparse
import datetime
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart          # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from order.status_codes import PurchaseOrderStatus        # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

AMAZON = Company.objects.filter(name__istartswith="Amazon").first()
PLACED = PurchaseOrderStatus.PLACED.value

ORDER = "113-5011479-9313006"
ASIN = "B0B5TN8LZB"
QTY = 1
UNIT = "16.99"
DATE = "2026-08-24"

print(f"supplier={AMAZON}")

existing = (PurchaseOrder.objects.filter(supplier_reference=ORDER).first()
            or PurchaseOrder.objects.filter(reference=ORDER).first())
if existing:
    print(f"SKIP (exists): {ORDER} -> {existing.reference}")
    sys.exit(0)

sp = SupplierPart.objects.filter(supplier=AMAZON, SKU=ASIN).first()
if not sp:
    print(f"!! no SupplierPart for {ASIN} under {AMAZON} -- expected a reorder of "
          f"the part on PO-0028. Not creating a part blind; investigate.")
    sys.exit(1)
print(f"reorder: {ASIN} -> part #{sp.part.pk} {sp.part.name[:60]}")

if not a.commit:
    print(f"~ WOULD create PO for {ORDER}: 1 line {ASIN} qty={QTY} unit=${UNIT}")
    sys.exit(0)

po = PurchaseOrder.objects.create(
    supplier=AMAZON,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=f"Amazon order {ORDER} - SHT31-D temp/humidity sensor 4-pack (reorder)"[:250],
    notes=("Auto-created from Amazon order confirmation 2026-08-24 (daytime sweep).\n"
           "Price read from the order-details page in Chrome, not the email:\n"
           "Item(s) Subtotal $16.99, Shipping $0.00, tax $0.00, Grand Total $16.99.\n"
           "No rewards points applied on this order.\n"
           f"Reorder of the same ASIN {ASIN} bought on 113-1351848-4611464 (PO-0028).\n"
           "PLACED, not received - receive by hand when the box arrives."),
    issue_date=datetime.date.fromisoformat(DATE),
    status=PLACED,
)
fresh = PurchaseOrder.objects.get(pk=po.pk)
print(f"+ {fresh.reference} supplier_ref={fresh.supplier_reference} "
      f"status={fresh.get_status_display()} reference_int={fresh.reference_int}")

li = PurchaseOrderLineItem.objects.create(
    order=po, part=sp, quantity=QTY,
    purchase_price=UNIT, purchase_price_currency="USD",
    notes=f"Amazon {ASIN}; unit price from the order-details page, not the email.",
)
print(f"  line: {ASIN} qty={QTY} unit=${UNIT} (line pk {li.pk})")
print(f"  lines now={po.lines.count()} status={po.get_status_display()} "
      f"(PLACED - NOT received, no stock created)")
