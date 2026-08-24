"""Decision queue item 5: MFC Machining & Design Services, order #MFCMD1086.
Approved by Scott 2026-08-24.

Fully itemised from the Shopify order confirmation of 2026-08-01, verbatim:

    ArmorGuard Stainless Way Covers x 1
    PCNC1100/1100M/1100M+/1100MX Z Cover     $349.95
    Subtotal $349.95   Shipping $29.95   Taxes $0.00   Total $379.90 USD

So the LINE price is $349.95 and the $379.90 total is not a unit price. Shipping
is recorded in the PO notes because there is no shipping field on the line.

Do NOT be misled by the Affirm/Shop Pay mail on this order: it shows a $94.98
payment, which is one instalment of four, not a price. Same class of error as
the Amazon rewards-points trap.

The vendor is a Shopify merchant, so the order mail comes from
store+70819512477@t.shopifyemail.com and the sender domain never names it. That
is why it was invisible to the sender-based sweep and only the shape-based one
found it. The store-id -> merchant mapping is added to vendor_registry.json so
the name is recoverable next time.

PLACED, not received - the box arrived 2026-08-22, but receiving is a human
checking it in.
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
from part.models import Part, PartCategory                # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()
DRY = not a.commit

ORDER = "MFCMD1086"
UNIT = "349.95"
SKU = "ARMORGUARD-Z-1100"
NAME = "Way Cover, Z-Axis, Stainless - Tormach PCNC1100 / 1100M / 1100M+ / 1100MX"
DESC = ("Stainless steel Z-axis way cover for the Tormach 1100-series mill. "
        "Fits PCNC1100, 1100M, 1100M+ and 1100MX. "
        "orig: ArmorGuard Stainless Way Covers - PCNC1100/1100M/1100M+/1100MX Z Cover")
KEYWORDS = ("way cover, way covers, waycover, bellows, chip guard, chip shield, "
            "Z axis, Z-axis, Tormach, PCNC1100, 1100M, 1100MX, ArmorGuard, "
            "stainless, mill accessory")

existing_po = (PurchaseOrder.objects.filter(supplier_reference=ORDER).first()
               or PurchaseOrder.objects.filter(reference=ORDER).first())
if existing_po:
    print(f"SKIP (exists): {ORDER} -> {existing_po.reference}")
    sys.exit(0)

cat = PartCategory.objects.filter(pk=87).first()
assert cat and "Accessories" in cat.pathstring, f"unexpected category: {cat}"
print(f"category = {cat.pathstring}")

company = Company.objects.filter(name__istartswith="MFC Machining").first()
if company:
    print(f"company exists: #{company.pk} {company.name}")
elif DRY:
    print("~ WOULD create Company 'MFC Machining & Design Services'")
else:
    company = Company.objects.create(
        name="MFC Machining & Design Services",
        description="Shopify merchant (store id 70819512477), trading as MFC OFFROAD, Dover NJ. Machining and design services; Tormach way covers. Contact jesse@mfcoffroad.com.",
        website="https://mfcmd.com",
        is_supplier=True,
    )
    assert Company.objects.get(pk=company.pk).name.startswith("MFC"), "company write did not stick"
    print(f"+ Company #{company.pk} {company.name}")

# Dedup across name, IPN and SKU before creating anything.
dupe = (Part.objects.filter(name=NAME).first()
        or Part.objects.filter(IPN=SKU).first()
        or (SupplierPart.objects.filter(SKU=SKU).first() or type("x", (), {"part": None})).part)
if dupe:
    print(f"dedup: matched existing part #{dupe.pk} {dupe.name[:50]}")
    part = dupe
elif DRY:
    print(f"~ WOULD create part {NAME!r}")
    part = None
else:
    part = Part.objects.create(
        name=NAME, description=DESC[:250], category=cat, IPN=SKU,
        keywords=KEYWORDS, active=True, purchaseable=True, component=False,
    )
    assert Part.objects.get(pk=part.pk).name == NAME, "part write did not stick"
    print(f"+ Part #{part.pk} {part.name[:60]}")

if DRY:
    print(f"~ WOULD create SupplierPart {SKU}")
    print(f"~ WOULD create PO for {ORDER}: 1 line qty=1 unit=${UNIT} (PLACED)")
    print("\nDRY RUN - nothing written")
    sys.exit(0)

sp = SupplierPart.objects.filter(supplier=company, SKU=SKU).first()
if not sp:
    sp = SupplierPart.objects.create(
        part=part, supplier=company, SKU=SKU,
        link="https://mfcmd.com",
        note="LOCAL placeholder SKU - the order confirmation published no vendor part number.",
    )
    print(f"+ SupplierPart {SKU} -> part #{part.pk}")

po = PurchaseOrder.objects.create(
    supplier=company,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=f"MFC order {ORDER} - Tormach 1100 Z-axis stainless way cover"[:250],
    notes=("Created 2026-08-24 from the Shopify order confirmation of 2026-08-01.\n"
           "Line price $349.95 read verbatim from the order summary.\n"
           "Subtotal $349.95 + Shipping $29.95 + Tax $0.00 = Total $379.90 USD.\n"
           "Shipping is NOT on the line - recorded here because the line has no field for it.\n"
           "The Affirm/Shop Pay $94.98 figure on this order is ONE INSTALMENT OF FOUR, not a price.\n"
           "Delivered 2026-08-22 (USPS 92346902673388000072740330). Left PLACED - receiving is a human job."),
    issue_date=datetime.date.fromisoformat("2026-08-01"),
    status=PurchaseOrderStatus.PLACED.value,
)
fresh = PurchaseOrder.objects.get(pk=po.pk)
print(f"+ {fresh.reference} supplier_ref={fresh.supplier_reference} "
      f"status={fresh.get_status_display()} reference_int={fresh.reference_int}")

li = PurchaseOrderLineItem.objects.create(
    order=po, part=sp, quantity=1,
    purchase_price=UNIT, purchase_price_currency="USD",
    notes="Unit price verbatim from the order summary line, not the order total.",
)
print(f"  line: {SKU} qty=1 unit=${UNIT} (line pk {li.pk})")
print(f"  lines={po.lines.count()} status={po.get_status_display()} (PLACED - no stock created)")
