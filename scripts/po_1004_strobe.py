"""Queue C: eBay order 09-15252-57599 (2026-10-04) -> new part + PO.

Vintage Radio Shack strobe light, listing title "vintage radio shack strobe
light WORKS". eBay item 188532551761, seller bethhh412. One unit.

PRICE SOURCE -- the eBay order-confirmation email, itemised:

    Price: $8.00
    Subtotal   $8.00
    Shipping   $6.03
    Total charged to x -7953   $14.03

Booked at $8.00, the ITEM line. The $14.03 total is 43% shipping and is not
the price (same trap as po_0919_sciencefair.py and AliExpress). The assert
reconciles against the SUBTOTAL.

SUPPLIER: eBay (Company #14), SKU = eBay item id, link = /itm/<item id>; order
number in supplier_reference only. Convention of sp #536/#686/#740 and the
Science Fair kit (#1238).

CATEGORY: flat `Equipment` (pk 30). A strobe is a finished, mains-powered
device, not a component and not an experimenter kit. Rejected, with what
eliminated each:
  - `Prototyping` -- the Science Fair kit went there because its siblings are
    breadboard/experimenter kits; a strobe has no such sibling.
  - `Electronics/Optoelectronics/LEDs` -- a component bin; a vintage strobe is
    almost certainly a xenon flash tube unit, not an LED, and is not a part.
  - `Equipment/Test Equipment` -- a party strobe is not a stroboscope
    tachometer; the listing gives no model number to say otherwise.
  - a new `Vintage`/`Lighting` category -- taxonomy decisions are not made
    unattended (14 shadow roots already open).
The model number is not in the confirmation; record it on arrival.

PACK 1. TARGET DATE = late end of the quoted range (Fri Oct 09 - Sat Oct 17).
NO IMAGE (image work is the 02:05 job's). PLACED, never received.
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

ORDER = "09-15252-57599"
ISSUE = datetime.date(2026, 10, 4)
ARRIVES = datetime.date(2026, 10, 17)         # late end of the quoted range
SUBTOTAL = 8.00                               # ITEM line, shipping excluded
SHIPPING = 6.03

ITEM_ID = "188532551761"
UNIT = "8.00"
QTY = 1
PACK = "1"

NAME = "Strobe Light, Radio Shack, vintage (model not yet recorded)"
DESC = "orig: vintage radio shack strobe light WORKS"
KEYWORDS = ("strobe, strobe light, stroboscope, flash, xenon, Radio Shack, "
            "RadioShack, Realistic, Archer, Tandy, vintage, retro, party light, "
            "light show, color organ, lighting effect")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

ebay = Company.objects.get(name="eBay")

# ---------------------------------------------------------------- idempotency
dup_po = PurchaseOrder.objects.filter(
    Q(supplier_reference=ORDER) | Q(reference=ORDER))
if dup_po.exists():
    sys.exit(f"!! PO already exists for {ORDER}: "
             f"{[p.reference for p in dup_po]} — nothing to do")

dupes = Part.objects.filter(
    Q(name__icontains="strobe") | Q(description__icontains="strobe")
    | Q(IPN=ITEM_ID)).distinct()
for d in dupes:
    print(f"  possible dupe: #{d.pk} active={d.active} {d.name}")
if dupes.exists():
    sys.exit("!! a strobe part already exists — resolve by hand")
if SupplierPart.objects.filter(supplier=ebay, SKU=ITEM_ID).exists():
    sys.exit(f"!! supplier part {ITEM_ID} already exists — resolve by hand")

total = float(UNIT) * QTY
print(f"reconcile: lines sum {total:.2f} vs email SUBTOTAL {SUBTOTAL:.2f} "
      f"(order total was {SUBTOTAL + SHIPPING:.2f} incl ${SHIPPING:.2f} shipping)")
assert abs(total - SUBTOTAL) < 0.005, "line price does not reconcile — refusing"

print(f"keywords: {len(KEYWORDS)} chars (limit 250)")
assert len(KEYWORDS) <= 250, f"keywords too long: {len(KEYWORDS)}"
assert len(NAME) <= 100, f"name too long: {len(NAME)}"

cat = PartCategory.objects.get(pk=30)
print(f"category: pk {cat.pk} {cat.pathstring} ({cat.parts.count()} parts)")
assert cat.pathstring == "Equipment", f"category moved: {cat.pathstring}"

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ---------------------------------------------------------------- part
part = Part(
    name=NAME,
    description=DESC,
    category=cat,
    IPN=ITEM_ID,
    keywords=KEYWORDS,
    component=True,
    purchaseable=True,
    assembly=False,
    notes=("Vintage Radio Shack strobe light, bought secondhand on eBay from "
           f"private seller bethhh412 (item {ITEM_ID}). The listing title says "
           "'WORKS' and nothing else; no model number, flash-tube type or "
           "condition grade was in the order confirmation.\n\n"
           "ON ARRIVAL: read the model / catalogue number off the unit and put "
           "it in the name (replace 'model not yet recorded'). It is mains "
           "powered and a xenon strobe holds a charged capacitor, so check the "
           "cord and case before plugging it in.\n\n"
           "Created by the queue C daytime sweep, 08:40 run 2026-10-04, from "
           f"eBay order {ORDER}. Category flat Equipment by elimination; see "
           "scripts/po_1004_strobe.py for what was rejected and why."),
)
part.save()
part.refresh_from_db()
assert part.name == NAME, "part name did not stick"
assert part.category_id == cat.pk, "category did not stick"
assert part.keywords == KEYWORDS, "keywords did not stick"
assert part.IPN == ITEM_ID, "IPN did not stick"
print(f"\nCREATED part #{part.pk} {part.name}  cat={part.category.pathstring}")

sp = SupplierPart(supplier=ebay, part=part, SKU=ITEM_ID,
                  link=f"https://www.ebay.com/itm/{ITEM_ID}")
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
    supplier=ebay,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=f"eBay order {ORDER} — vintage Radio Shack strobe light",
    issue_date=ISSUE,
    target_date=ARRIVES,
    status=PurchaseOrderStatus.PLACED.value,
    notes=("Auto-created by the queue C daytime sweep, 08:40 run 2026-10-04.\n\n"
           "PRICE SOURCE: the eBay order-confirmation email, itemised — Price: "
           "$8.00, Subtotal $8.00, Shipping $6.03, Total charged $14.03. The "
           "line is booked at the ITEM price of $8.00; the $14.03 total is 43% "
           "shipping and was deliberately not used.\n\n"
           "Sold by the private eBay seller bethhh412; supplier is eBay as the "
           "marketplace, per convention.\n\n"
           "VINTAGE SECONDHAND, listing says 'WORKS'. Record the model number "
           "on the part when it arrives.\n\n"
           "TARGET DATE is the LATE end of the quoted range (Fri Oct 09 - Sat "
           "Oct 17) so it does not read OVERDUE while legitimately in transit.\n\n"
           "PACK: 1.\n\n"
           "PLACED, not received. Receive with receive_po.py when checked in."),
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
    notes=("Per-item price from the eBay order confirmation: one strobe at "
           "$8.00. Shipping of $6.03 deliberately excluded."))
li.save()
li.refresh_from_db()
assert float(li.purchase_price.amount) == float(UNIT), \
    f"price did not stick: {li.purchase_price}"
print(f"    line: qty {li.quantity} @ {li.purchase_price}")

po.refresh_from_db()
booked = sum(float(l.purchase_price.amount) * float(l.quantity)
             for l in po.lines.all())
print(f"\nDONE  {po.reference}  lines={po.lines.count()}  booked=${booked:.2f}"
      f"  (email subtotal ${SUBTOTAL:.2f})")
assert abs(booked - SUBTOTAL) < 0.005, "booked total drifted from the email"
