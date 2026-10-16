"""Queue C, 16:40 daytime sweep 2026-10-16: one Amazon order -> one PO.

  113-7454208-3648243  placed 2026-10-16, ship to The Villages FL (LRD), "Arriving tomorrow" (10-17)
    Silkland 20Gbps USB C Data Cable Right Angle, 1.6FT USB C to USB C, 240W
    B0DKHDHCKF  sold by Silkland-US  $11.68 x1

AMAZON PRICE SOURCE -- the order-details page: Item(s) Subtotal $11.68, shipping
$0.00, tax $0.82, Grand Total $12.50. The 12.50 grand total includes tax and is
not the price.

Same day, 113-5895684-5016234 is the SAME cable, cancelled -- no PO, skipped.
Same day, 113-3835894-2862621 is an AROMA rice cooker -- household, OUT
(kitchen appliance, same precedent as the Bounty / Glad / LL Bean household skips).

Dry run lists existing USB-C cable parts; if one is the same cable, pass
--part <pk> to reuse it instead of creating. --cat <pk> --commit creates.
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

RUN = "16:40 daytime sweep 2026-10-16"
TODAY = datetime.date(2026, 10, 16)
ORDER = "113-7454208-3648243"
ASIN = "B0DKHDHCKF"
PRICE = "11.68"

NAME = "Cable, USB-C to USB-C, 0.5 m (1.6 ft), right-angle, 20 Gbps, 240 W, Silkland"
DESC = ("orig: Silkland 20Gbps USB C Data Cable Right Angle, 1.6FT USB C to USB C Cable | 90 "
        "Degree, 240W Charging, Short High Speed Data Transfer Cable, 5K/4K 60Hz Monitor Display; "
        "Amazon B0DKHDHCKF")
KW = ("USB-C, USB C, type-C, cable, USB-C to USB-C, right angle, 90 degree, 20Gbps, USB 3.2, "
      "240W, PD, short cable, 0.5m, 1.6ft, data cable, display, Silkland")
SP_DESC = "Silkland 1.6 ft right-angle USB-C to USB-C 20 Gbps 240 W cable (Silkland-US)"
NOTES = ("Short USB-C to USB-C cable, one right-angle end, 20 Gbps data, 240 W PD, 4K/5K "
         "display alt-mode. Counted as ONE cable.\n\n"
         f"Ordered 2026-10-16 to The Villages FL (LRD), Amazon {ORDER}.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--cat", type=int)
ap.add_argument("--part", type=int)
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

# ------------------------------------------------------------ checks
dup = PurchaseOrder.objects.filter(Q(supplier_reference=ORDER) | Q(reference=ORDER))
if dup.exists():
    sys.exit(f"!! PO already exists for {ORDER}: {[p.reference for p in dup]}")
sp_existing = SupplierPart.objects.filter(SKU__iexact=ASIN).first()
if sp_existing:
    print(f"  supplier part {ASIN} already exists: sp #{sp_existing.pk} -> part #{sp_existing.part_id}")
hits = Part.objects.filter(Q(name__icontains="silkland") | Q(description__icontains="silkland")
                           | Q(description__icontains=ASIN)
                           | (Q(name__icontains="usb") & Q(name__icontains="cable")))
for h in hits:
    print(f"  existing usb-cable part #{h.pk}: {h.name}  active={h.active}  cat={h.category_id}: {h.category}")
assert len(KW) <= 250 and len(NAME) <= 100 and len(DESC) <= 250, (len(KW), len(NAME), len(DESC))

print("cable categories:")
for c in PartCategory.objects.filter(Q(name__icontains="cable") | Q(name__icontains="usb")):
    print(f"  {c.pk}: {c.pathstring}  ({c.parts.count()} parts)")

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --cat <pk> --commit (or --part <pk> --commit to reuse)")

# ------------------------------------------------------------ part
if sp_existing:
    sp = sp_existing
    print(f"REUSING sp #{sp.pk} part #{sp.part_id}")
elif args.part:
    part = Part.objects.get(pk=args.part)
    sp = SupplierPart(supplier=amazon, part=part, SKU=ASIN,
                      link=f"https://www.amazon.com/dp/{ASIN}", description=SP_DESC)
    sp.pack_quantity = "1"
    sp.save()
    sp.refresh_from_db()
    assert sp.SKU == ASIN and sp.part_id == part.pk, "sp did not stick"
    print(f"REUSING part #{part.pk} {part.name}; new sp #{sp.pk}")
else:
    cat = PartCategory.objects.get(pk=args.cat)
    part = Part(name=NAME, description=DESC, category=cat, keywords=KW,
                component=False, purchaseable=True, assembly=False,
                notes=NOTES + f"\n\nCreated by the queue C daytime sweep, {RUN}.")
    part.save()
    part.refresh_from_db()
    assert part.name == NAME and part.category_id == cat.pk and part.keywords == KW
    sp = SupplierPart(supplier=amazon, part=part, SKU=ASIN,
                      link=f"https://www.amazon.com/dp/{ASIN}", description=SP_DESC)
    sp.pack_quantity = "1"
    sp.save()
    sp.refresh_from_db()
    assert sp.SKU == ASIN and sp.part_id == part.pk, "sp did not stick"
    print(f"CREATED part #{part.pk} {part.name}  cat={part.category.pathstring}  sp #{sp.pk}")

# ------------------------------------------------------------ PO
po = PurchaseOrder(
    supplier=amazon,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=f"Amazon order {ORDER} — Silkland right-angle USB-C cable (to The Villages FL)",
    issue_date=TODAY, target_date=datetime.date(2026, 10, 17),
    status=PurchaseOrderStatus.PLACED.value,
    notes=(f"Auto-created by the queue C daytime sweep, {RUN}.\n\n"
           "Ships to The Villages FL (LRD).\n\n"
           f"PRICE SOURCE: the order-details page — ${PRICE} for one cable, sold by "
           "Silkland-US. Item(s) Subtotal $11.68, shipping $0.00, tax $0.82, Grand Total $12.50.\n\n"
           "The $12.50 grand total includes tax; it is not the price and is deliberately not "
           "on the line. Order 113-5895684-5016234 the same day was the same cable, cancelled.\n\n"
           "PLACED, not received."),
)
po.save()
po.refresh_from_db()
assert po.status == PurchaseOrderStatus.PLACED.value
assert po.supplier_reference == ORDER and po.reference != ORDER
li = PurchaseOrderLineItem(
    order=po, part=sp, quantity=1,
    purchase_price=PRICE, purchase_price_currency="USD",
    notes=f"Per-item price from the Amazon order-details page (${PRICE}), NOT the $12.50 "
          "grand total.")
li.save()
li.refresh_from_db()
assert float(li.purchase_price.amount) == float(PRICE), li.purchase_price
po.refresh_from_db()
print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
      f"target={po.target_date} lines={po.lines.count()} @ {li.purchase_price}")
