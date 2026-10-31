#!/usr/bin/env python3
"""Price PO-0273 (Walmart 2000155-68010813, 2x Sterilite 6 qt 10-pack) so it can be deployed.

Measured 2026-10-31 from the Walmart order-confirmation email (help@walmart.com,
2026-10-27): "Order total ... Includes all fees, taxes and discounts $23.50",
2 items, card ending 1009. The email does not itemize, so the line carries
$23.50 / 2 = $11.75 per 10-pack, tax included. Rejected backing tax out at a
guessed rate: that would be a modelled number dressed as a price.
"""
import os, sys
from decimal import Decimal
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from order.models import PurchaseOrder, PurchaseOrderLineItem
from plugins.notes_compat import note_append, note_text

COMMIT = "--commit" in sys.argv
po = PurchaseOrder.objects.get(reference="PO-0273")
ln = po.lines.get()
print(f"{po.reference} line {ln.pk} qty {ln.quantity} price {ln.purchase_price} -> 11.75")
print(f"description: {po.description}")
if not COMMIT:
    print("DRY RUN"); sys.exit(0)
PurchaseOrderLineItem.objects.filter(pk=ln.pk).update(purchase_price=Decimal("11.75"), purchase_price_currency="USD")
desc = po.description.replace(" [needs-price]", "")
PurchaseOrder.objects.filter(pk=po.pk).update(description=desc)
note_append(po, ("2026-10-31 PRICE: $11.75 per 10-pack = Walmart order total $23.50 "
                 "(fees, tax and discounts included) / 2. The confirmation email does not itemize."))
ln.refresh_from_db(); po.refresh_from_db()
assert ln.purchase_price.amount == Decimal("11.75"), ln.purchase_price
assert "[needs-price]" not in po.description
print(f"ok: {ln.purchase_price}  {po.description}")
