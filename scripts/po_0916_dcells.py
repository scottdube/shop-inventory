"""Queue C: Amazon order 113-4086150-1595402 (2026-09-16) -> new part + PO.

Amazon Basics 12-Pack D Cell Alkaline, ASIN B00MH4QKP6, Subscribe & Save,
auto-delivered every 3 months.

WHY THIS ONE IS IMPORTED WHEN THE OTHER TWO IN THE SAME WINDOW ARE NOT.
The 12:40 sweep saw three un-imported Amazon orders on 09-15/09-16: these D
cells, Taste of the Wild dog food (113-6937439-0424225) and Glad trash bags
(113-3782580-9480223). All three are Subscribe & Save household auto-deliveries,
so "it is a subscription" does not separate them and is not the test.

The test is PRECEDENT, not judgement: part #1176 "Alkaline Battery AAA 1.5V
(LR03)" already exists, created by PO-0161 from Amazon order
113-8216914-9857847 on 2026-09-06 -- the SAME vendor, the SAME Amazon Basics
alkaline line, the SAME Subscribe & Save shape. Primary cells are stocked here
(they feed calipers, the DRO, test meters, torches). Dog food and trash bags
have no part, no precedent and no shop use. Importing the batteries is applying
an existing ruling; importing the other two would be inventing one.

PRICE SOURCE -- the order-details page, per item:

    Amazon Basics 12-Pack D Cell Alkaline   17.49 x 1 pack
                                            -----
                                            17.49

**Booked at $17.49, the item-line price, NOT the $14.87 Grand Total.** The page
reads Item(s) Subtotal $17.49, shipping $0.00, tax $0.00, Subscribe & Save
-$2.62, Grand Total $14.87.

This is NOT settled by the rewards-points rule (points are a payment method; a
Subscribe & Save discount is a real price reduction), so it lands squarely on
the OPEN decision item `amazon-promo-discount-vs-item-price`. It is not queued
again here -- a second copy of a live question is noise, and the queue already
carries a complaint about exactly that.

It is decided the same way the last one was, and that was MEASURED rather than
assumed: PO-0161 booked $13.70 against an order whose page read subtotal $13.70,
Subscribe & Save -$2.06, Grand Total $11.64. The install's existing convention
is the PRE-discount item-line price. Followed here for consistency; if Scott
rules the other way on that open item, both POs move together.

PACK: 12 pieces, carried on the supplier part as pack_quantity, written through
.save() (never .update() -- only pack_quantity_native is read at receive time,
and .update() skips clean()). Stock counts PIECES: receiving this books 12 cells
at $1.4575 each, not one unit at $17.49.

PLACED, never received. Arriving Monday 2026-09-21; a human checks it in.
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

ORDER = "113-4086150-1595402"
ISSUE = datetime.date(2026, 9, 16)
ARRIVES = datetime.date(2026, 9, 21)
SUBTOTAL = 17.49

ASIN = "B00MH4QKP6"
UNIT = "17.49"
QTY = 1
PACK = "12"

NAME = "Alkaline Battery D 1.5V (LR20)"
DESC = ("orig: Amazon Basics 12-Pack D Cell Alkaline Batteries, 1.5 Volt, "
        "5-Year Shelf Life, Long-Lasting Power, Reliable for Clocks and "
        "Emergency Use")
KEYWORDS = ("D, LR20, R20, MN1300, D cell, mono, alkaline, primary cell, "
            "battery, batteries, 1.5V, 1.5 volt, non-rechargeable, disposable, "
            "torch, flashlight, lantern, clock, emergency, consumable, "
            "Amazon Basics")

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
dupes = (Part.objects.filter(name__icontains="LR20")
         | Part.objects.filter(name__icontains="D Cell")
         | Part.objects.filter(IPN=ASIN)
         | Part.objects.filter(description__icontains=ASIN)).distinct()
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
cat = PartCategory.objects.get(pathstring="Electronics/Power")
part = Part(
    name=NAME,
    description=DESC,
    category=cat,
    IPN=ASIN,
    keywords=KEYWORDS,
    component=True,
    purchaseable=True,
    assembly=False,
    notes=("Primary (non-rechargeable) D cell, LR20 / R20 / MN1300. Counted in "
           "PIECES; the Amazon supplier part carries the 12-pack.\n\n"
           "Created by the queue C daytime sweep, 12:40 run 2026-09-16, from "
           f"Amazon order {ORDER}. Sibling of part #1176 (AAA, LR03), same "
           "Amazon Basics alkaline line on Subscribe & Save."),
)
part.save()
part.refresh_from_db()
assert part.name == NAME, "part name did not stick"
assert part.category_id == cat.pk, "category did not stick"
assert part.keywords == KEYWORDS, "keywords did not stick"
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
    description=f"Amazon order {ORDER} — D cell alkaline batteries, 12-pack",
    issue_date=ISSUE,
    target_date=ARRIVES,
    status=PurchaseOrderStatus.PLACED.value,
    notes=("Auto-created by the queue C daytime sweep, 12:40 run 2026-09-16.\n\n"
           "PRICE SOURCE: the order-details page, per item — $17.49. The Grand "
           "Total is $14.87 after a Subscribe & Save discount of $2.62. Booked "
           "at the PRE-discount item-line price, matching PO-0161 (the AAA "
           "cells, 2026-09-06), which booked $13.70 against a $11.64 Grand "
           "Total under the identical discount shape. The open decision item "
           "`amazon-promo-discount-vs-item-price` still governs; if it is "
           "ruled the other way, this PO and PO-0161 move together.\n\n"
           "PACK: 12 pieces on the supplier part. Receiving books 12 cells at "
           "$1.4575 each, not 1 unit at $17.49.\n\n"
           "Subscribe & Save, auto-delivered every 3 months — expect this "
           "order shape again around 2026-12-16.\n\n"
           "PLACED, not received. Arriving 2026-09-21; receive with "
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
    notes=("Per-item price from the Amazon order-details page: one 12-pack at "
           "$17.49. Grand Total was $14.87 after a $2.62 Subscribe & Save "
           "discount; the pre-discount line price is booked, per PO-0161."))
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
