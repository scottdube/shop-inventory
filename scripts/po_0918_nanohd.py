"""Queue C: Amazon order 113-7781321-8645014 (2026-09-18) -> new part + PO.

Ubiquiti UniFi nanoHD access point, ASIN B07FFNTLJD, sold by the marketplace
seller "Discover Savings". One unit, arriving 2026-09-19.

PRICE SOURCE -- the order-details page, per item:

    Ubiquiti Networks UniFi nanoHD ... Access Point   61.99 x 1
                                                      -----
                                                      61.99

**Booked at $61.99. The email and the order list both say Grand Total $0.00.**
That number is worth nothing here and is exactly the case the standing rule was
written for: the page reads Item(s) Subtotal $61.99, shipping $0.00, tax $0.00,
Gift Card -$40.07, Rewards Points -$21.92, Grand Total $0.00. Payment method is
not price -- a gift card and a points balance paid for this, so the order cost
$0.00 out of pocket and the access point is still a $61.99 asset. Booking $0.00
would have put a free access point on the books.

This is NOT the open `amazon-promo-discount-vs-item-price` question and is not
queued against it. That item is about whether a genuine PRICE REDUCTION
(Subscribe & Save) should be booked pre- or post-discount. Nothing here reduced
the price; two payment instruments settled it. The rewards-points rule in
section 3 of the task file already decides this shape outright.

CATEGORY: flat `RF` (pk 35), by precedent rather than judgement -- part #930,
the MikroTik Metal 2SHPn 2.4GHz radio, is the nearest thing in the system and
lives there. `Electronics/RF` (pk 62) exists and holds ZERO parts; it is one of
the documented shadow roots, and the flat side wins here as it usually does.

PACK: 1. A single access point, not a multipack -- checked, because 688 of 706
supplier parts once carried a wrong pack.

NO IMAGE IS ATTACHED. Harvesting an image at part creation is an OPEN decision
item (`harvest-image-at-part-creation`, queued 2026-09-15) and is not approved;
image work belongs to the 02:05 enrich job, not to this sweep.

PLACED, never received. A human checks it in.
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

ORDER = "113-7781321-8645014"
ISSUE = datetime.date(2026, 9, 18)
ARRIVES = datetime.date(2026, 9, 19)
SUBTOTAL = 61.99

ASIN = "B07FFNTLJD"
UNIT = "61.99"
QTY = 1
PACK = "1"

NAME = "Ubiquiti UniFi nanoHD Wi-Fi Access Point (UAP-nanoHD)"
DESC = ("orig: Ubiquiti Networks UniFi nanoHD Internal 1733Mbit/s Power Over "
        "Ethernet (PoE) White WLAN Access Point")
KEYWORDS = ("UniFi, nanoHD, UAP-nanoHD, Ubiquiti, UBNT, access point, AP, WAP, "
            "wireless access point, WLAN, Wi-Fi, wifi, 802.11ac, wave 2, "
            "MU-MIMO, dual band, 2.4GHz, 5GHz, 1733Mbps, PoE, 802.3af, "
            "ceiling mount, network, networking, controller managed")

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

# Duplicate scan across name, description, IPN and supplier SKU before creating.
dupes = (Part.objects.filter(name__icontains="nanoHD")
         | Part.objects.filter(name__icontains="UniFi")
         | Part.objects.filter(name__icontains="Access Point")
         | Part.objects.filter(IPN=ASIN)
         | Part.objects.filter(description__icontains=ASIN)
         | Part.objects.filter(description__icontains="nanoHD")).distinct()
for d in dupes:
    print(f"  possible dupe: #{d.pk} active={d.active} {d.name}")
if SupplierPart.objects.filter(supplier=amazon, SKU=ASIN).exists():
    sys.exit(f"!! supplier part {ASIN} already exists — resolve by hand")

total = float(UNIT) * QTY
print(f"reconcile: lines sum {total:.2f} vs page subtotal {SUBTOTAL:.2f}")
assert abs(total - SUBTOTAL) < 0.005, "line price does not reconcile — refusing"

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ---------------------------------------------------------------- part
cat = PartCategory.objects.get(pk=35)
assert cat.pathstring == "RF", f"category moved: {cat.pathstring}"
part = Part(
    name=NAME,
    description=DESC,
    category=cat,
    IPN=ASIN,
    keywords=KEYWORDS,
    component=True,
    purchaseable=True,
    assembly=False,
    notes=("Ubiquiti UniFi nanoHD (UAP-nanoHD): 802.11ac Wave 2 dual-band "
           "indoor access point, 4x4 MU-MIMO on 5GHz, 2x2 on 2.4GHz, rated "
           "1733Mbit/s on 5GHz. Single Gigabit uplink, powered by 802.3af "
           "PoE. Ceiling/wall mount, managed by a UniFi controller.\n\n"
           "The vendor title on the order page is cut off mid-word at "
           "\"Access poin\"; the description restores the final letter and "
           "changes nothing else.\n\n"
           "Created by the queue C daytime sweep, 16:40 run 2026-09-18, from "
           f"Amazon order {ORDER}. Nearest sibling is part #930 (MikroTik "
           "Metal 2SHPn), which set this category."),
)
part.save()
part.refresh_from_db()
assert part.name == NAME, "part name did not stick"
assert part.category_id == cat.pk, "category did not stick"
assert part.keywords == KEYWORDS, "keywords did not stick"
assert part.IPN == ASIN, "IPN did not stick"
print(f"\nCREATED part #{part.pk} {part.name}  cat={part.category.pathstring}")

sp = SupplierPart(supplier=amazon, part=part, SKU=ASIN,
                  link=f"https://www.amazon.com/dp/{ASIN}")
sp.pack_quantity = PACK          # .save() -> clean() -> pack_quantity_native
sp.save()
sp.refresh_from_db()
assert str(sp.pack_quantity) == PACK, f"pack text did not stick: {sp.pack_quantity}"
assert float(sp.pack_quantity_native) == float(PACK), \
    f"pack_quantity_native did not stick: {sp.pack_quantity_native}"
print(f"  sp #{sp.pk} SKU={sp.SKU} pack={sp.pack_quantity} "
      f"native={sp.pack_quantity_native}")

# ---------------------------------------------------------------- PO
po = PurchaseOrder(
    supplier=amazon,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=f"Amazon order {ORDER} — UniFi nanoHD access point",
    issue_date=ISSUE,
    target_date=ARRIVES,
    status=PurchaseOrderStatus.PLACED.value,
    notes=("Auto-created by the queue C daytime sweep, 16:40 run 2026-09-18.\n\n"
           "PRICE SOURCE: the order-details page, per item — $61.99.\n\n"
           "THE GRAND TOTAL ON THIS ORDER IS $0.00 AND IS NOT THE PRICE. The "
           "page reads Item(s) Subtotal $61.99, shipping $0.00, tax $0.00, "
           "Gift Card -$40.07, Rewards Points -$21.92, Grand Total $0.00. A "
           "gift-card balance and a points balance are payment instruments, "
           "not a discount; the access point is a $61.99 asset that happened "
           "to cost nothing out of pocket. This is the exact failure the "
           "standing rule against Amazon Grand Totals names.\n\n"
           "Sold by the marketplace seller \"Discover Savings\", not by "
           "Amazon directly; the supplier is Amazon as the marketplace, per "
           "the convention used by every other marketplace PO here.\n\n"
           "PACK: 1 — a single access point.\n\n"
           "PLACED, not received. Arriving 2026-09-19; receive with "
           "receive_po.py when the box is physically checked in."),
)
po.save()
po.refresh_from_db()
assert po.status == PurchaseOrderStatus.PLACED.value, "PO status did not stick"
assert po.supplier_reference == ORDER, "supplier_reference did not stick"
assert po.reference != ORDER, "vendor number leaked into reference"
print(f"\nCREATED {po.reference} supplier_ref={po.supplier_reference}")

li = PurchaseOrderLineItem(
    order=po, part=sp, quantity=QTY,
    purchase_price=UNIT, purchase_price_currency="USD",
    notes=("Per-item price from the Amazon order-details page: one access "
           "point at $61.99. The Grand Total is $0.00 because a $40.07 gift "
           "card and $21.92 of rewards points paid for it — payment method, "
           "not price."))
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
