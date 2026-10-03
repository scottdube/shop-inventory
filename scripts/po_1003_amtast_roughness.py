"""Queue C, 02:05 enrich run 2026-10-03: one order -> one PO.

  Amazon 113-2416815-5563466  placed 2026-10-02, "Arriving tomorrow" (2026-10-04)
    AMTAST AMT220 surface roughness tester   B0CN6KCZPF   sold by AMTAST   $759.99

AMAZON PRICE SOURCE -- the order-details page: Item(s) Subtotal $759.99,
shipping 0, tax 0, Gift Card -$47.82, Rewards Points -$10.90, Grand Total
$701.27. One item, qty 1.

THE GRAND TOTAL IS NOT THE PRICE. $701.27 is cash after a gift-card balance and
Visa points were applied as payment methods -- exactly the trap the task file
names. Booking $701.27 would understate the instrument by $58.72. The line
carries $759.99, the per-item figure the page prints twice.

No duplicate: part_find on AMTAST / AMT220 / B0CN6KCZPF / roughness /
profilometer / "surface finish" / "Ra meter" -> 0 hits, and Tooling/Measuring
holds no roughness instrument. Filed in Tooling/Measuring beside the
micrometers and height gauges rather than Equipment/Test Equipment: every
existing metrology instrument lives there, and a second home for the same kind
of thing is how the shadow-root taxonomies started.

AMTAST stays in the name: here it is the maker (the listing says sold by
AMTAST), not a reseller prefix, and AMT220 alone does not identify the product.

No IPN (follows the recent creations, e.g. #1266). No default_location.
PLACED, never received.
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
from part.models import Part, PartCategory  # noqa: E402

RUN = "02:05 enrich run 2026-10-03"
TODAY = datetime.date(2026, 10, 2)

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

AMZ_ORDER = "113-2416815-5563466"
AMZ_ASIN = "B0CN6KCZPF"
AMZ_PRICE = "759.99"
MODEL = "AMT220"

# ------------------------------------------------------------ checks
dup = PurchaseOrder.objects.filter(Q(supplier_reference=AMZ_ORDER) | Q(reference=AMZ_ORDER))
if dup.exists():
    sys.exit(f"!! PO already exists for {AMZ_ORDER}: {[p.reference for p in dup]}")
if SupplierPart.objects.filter(SKU__iexact=AMZ_ASIN).exists():
    sys.exit(f"!! supplier part {AMZ_ASIN} already exists")

cat = PartCategory.objects.get(name="Measuring", parent__name="Tooling")
print(f"category {cat.pk} {cat.pathstring}")

NAME = "AMTAST AMT220 Handheld Surface Roughness Tester, 22 Parameters"
DESC = ("orig: AMTAST Surface Roughness Meter Digital Surface Gauge Handheld Surface "
        "Roughness Tester Meter with 22 Parameters Portable Profilometer for Accurate "
        "Surface Measurement (Model AMT220); Amazon B0CN6KCZPF")
KW = ("surface roughness, roughness tester, profilometer, surface finish, finish gauge, "
      "Ra, Rz, Rq, Ra meter, microinch, stylus, metrology, surface gauge, AMT220, AMTAST")
assert len(KW) <= 250 and len(NAME) <= 100 and len(DESC) <= 250, (len(KW), len(NAME), len(DESC))
hits = Part.objects.filter(Q(name=NAME) | Q(description__icontains=MODEL)
                           | Q(IPN__iexact=MODEL) | Q(keywords__icontains=MODEL)
                           | Q(name__icontains="roughness"))
if hits.exists():
    sys.exit(f"!! a part with this name / model exists: {[h.pk for h in hits]}")

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ------------------------------------------------------------ PO
po = PurchaseOrder(
    supplier=amazon,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=AMZ_ORDER,
    description=f"Amazon order {AMZ_ORDER} — AMTAST AMT220 surface roughness tester",
    issue_date=TODAY, target_date=datetime.date(2026, 10, 4),
    status=PurchaseOrderStatus.PLACED.value,
    notes=(f"Auto-created by the queue C overnight sweep, {RUN}.\n\n"
           "PRICE SOURCE: the order-details page — $759.99 for one AMTAST AMT220, "
           "sold by AMTAST. Item(s) Subtotal $759.99, shipping $0.00, tax $0.00, "
           "Gift Card -$47.82, Rewards Points -$10.90, Grand Total $701.27.\n\n"
           "The $701.27 grand total is cash after a gift-card balance and Visa points "
           "were applied as PAYMENT METHODS. It is not the price and is deliberately "
           "not on the line.\n\n"
           "PLACED, not received."),
)
po.save()
po.refresh_from_db()
assert po.status == PurchaseOrderStatus.PLACED.value
assert po.supplier_reference == AMZ_ORDER and po.reference != AMZ_ORDER
print(f"\nCREATED {po.reference} supplier_ref={po.supplier_reference}")

part = Part(
    name=NAME, description=DESC, category=cat, keywords=KW,
    component=False, purchaseable=True, assembly=False,
    notes=("Handheld stylus surface roughness tester (profilometer), AMTAST model "
           "AMT220, 22 roughness parameters per the listing.\n\n"
           "Specs beyond the listing title are not recorded — read them off the "
           "unit or its manual at receive, not off the marketplace page.\n\n"
           f"Created by the queue C overnight sweep, {RUN}, from Amazon order "
           f"{AMZ_ORDER}."),
)
part.save()
part.refresh_from_db()
assert part.name == NAME and part.category_id == cat.pk and part.keywords == KW
print(f"CREATED part #{part.pk} {part.name}  cat={part.category.pathstring}")

sp = SupplierPart(supplier=amazon, part=part, SKU=AMZ_ASIN,
                  link=f"https://www.amazon.com/dp/{AMZ_ASIN}",
                  description="AMTAST AMT220 surface roughness tester")
sp.pack_quantity = "1"
sp.save()
sp.refresh_from_db()
assert sp.SKU == AMZ_ASIN and sp.part_id == part.pk, "sp did not stick"
print(f"  sp #{sp.pk} SKU={sp.SKU} -> part #{part.pk}")

li = PurchaseOrderLineItem(
    order=po, part=sp, quantity=1,
    purchase_price=AMZ_PRICE, purchase_price_currency="USD",
    notes="Per-item price from the Amazon order-details page ($759.99), NOT the "
          "$701.27 grand total (gift card + points applied).")
li.save()
li.refresh_from_db()
assert float(li.purchase_price.amount) == float(AMZ_PRICE), li.purchase_price
print(f"  line qty {li.quantity} @ {li.purchase_price}")

po.refresh_from_db()
print(f"{po.reference} {po.supplier.name} {po.supplier_reference} status={po.status} "
      f"lines={po.lines.count()}")
