"""Queue C: eBay order 27-15157-16681 (2026-09-19) -> new part + PO.

Science Fair 75-in-1 Electronic Project Kit, Radio Shack 28-247, wood case.
eBay item 227521676914, seller magicamulet. Best-offer accepted, one unit.

PRICE SOURCE -- the eBay order-confirmation email, which is itemised and states
the per-item price directly:

    Price: $25.00
    Subtotal   $25.00
    Shipping   $14.10
    Total charged to x -7953   $39.10

Booked at $25.00, the ITEM line. The $39.10 total is NOT the price: it carries
$14.10 of shipping, which on a $25 item is 36% of the charge -- the same trap
already written down for AliExpress, where dividing the total ran 37% high. The
assert at the bottom reconciles against the SUBTOTAL, not the total.

SUPPLIER: eBay (Company #14), SKU = the eBay ITEM id, link = /itm/<item id>.
The order number goes in supplier_reference only. That is the convention set by
sp #536, #686 and #740 (the T400, imported by the 22:40 run yesterday). The
seller is a private eBay account, not a Company -- same marketplace convention
as Amazon.

CATEGORY: flat `Prototyping`, by precedent rather than taste. A 75-in-1 is a
self-contained experimenter platform -- spring terminals, fixed component set,
build-by-diagram -- so its real siblings are the breadboard/experimenter kits
that already live there: #80 Makeronics Solderless 3220 Tie-Point Breadboard
Super Kit, #157 Paxcoo Breadboards Kit, #384 Minidodoca Breadboard Kit, #218
AUSTOR PCB prototype kit. Rejected, with what eliminated each:
  - `Projects` (pk 132) -- that root holds parts allocated to specific builds,
    not purchasable stock items.
  - `Electronics/Modules/Dev Boards` (pk 70) -- the one starter kit there
    (#734 Keyestudio) is INACTIVE, and it is a documented Electronics shadow
    root where the flat side usually wins.
  - a new `Education`/`Vintage` category -- 14 shadow roots are already open;
    creating a root on my own judgement during an unattended run is a taxonomy
    decision, not transcription.

PACK: 1. One kit, one unit. Not an assortment to be exploded into pieces: the
components are wired down to a board and are not separately stockable, which is
the documented assortment-is-not-a-multipack line.

TARGET DATE: the email gives a RANGE, Thu Sep 24 - Thu Oct 01. Booked as the
LATE end (2026-10-01) so the order does not read OVERDUE on the purchasing
screen while it is legitimately still in transit.

CONDITION: vintage secondhand. The listing title says "NICE!" and nothing else;
no condition grade was stated in the confirmation and none is recorded here.

NO IMAGE IS ATTACHED. Harvesting an image at part creation is an OPEN decision
item (`harvest-image-at-part-creation`, 2026-09-15) and is not approved; image
work belongs to the 02:05 enrich job, not to this sweep.

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

ORDER = "27-15157-16681"
ISSUE = datetime.date(2026, 9, 19)
ARRIVES = datetime.date(2026, 10, 1)          # late end of the quoted range
SUBTOTAL = 25.00                              # ITEM line, shipping excluded
SHIPPING = 14.10

ITEM_ID = "227521676914"
UNIT = "25.00"
QTY = 1
PACK = "1"

NAME = "Science Fair 75-in-1 Electronic Project Kit, Radio Shack 28-247, wood case"
DESC = "orig: Science Fair 75 In 1 Electronic Project Kit - Radio Shack Wood - 28-247 NICE!"
KEYWORDS = ("Science Fair, 75 in 1, 75-in-1, Radio Shack, RadioShack, 28-247, "
            "electronic project kit, experimenter, experiment board, spring "
            "terminal, learning kit, educational, breadboard alternative, "
            "vintage, retro, project lab, Tandy")

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

# Duplicate scan across name, description, IPN and supplier SKU before creating.
dupes = (Part.objects.filter(name__icontains="science fair")
         | Part.objects.filter(name__icontains="radio shack")
         | Part.objects.filter(name__icontains="75-in-1")
         | Part.objects.filter(name__icontains="75 in 1")
         | Part.objects.filter(IPN=ITEM_ID)
         | Part.objects.filter(description__icontains="28-247")).distinct()
for d in dupes:
    print(f"  possible dupe: #{d.pk} active={d.active} {d.name}")
if SupplierPart.objects.filter(supplier=ebay, SKU=ITEM_ID).exists():
    sys.exit(f"!! supplier part {ITEM_ID} already exists — resolve by hand")

total = float(UNIT) * QTY
print(f"reconcile: lines sum {total:.2f} vs email SUBTOTAL {SUBTOTAL:.2f} "
      f"(order total was {SUBTOTAL + SHIPPING:.2f} incl ${SHIPPING:.2f} shipping)")
assert abs(total - SUBTOTAL) < 0.005, "line price does not reconcile — refusing"

print(f"keywords: {len(KEYWORDS)} chars (limit 250)")
assert len(KEYWORDS) <= 250, f"keywords too long: {len(KEYWORDS)}"
assert len(NAME) <= 100, f"name too long: {len(NAME)}"

cat = PartCategory.objects.get(name="Prototyping", parent__isnull=True)
print(f"category: pk {cat.pk} {cat.pathstring} ({cat.parts.count()} parts)")
assert cat.pathstring == "Prototyping", f"category moved: {cat.pathstring}"

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
    notes=("Radio Shack Science Fair 75-in-1 Electronic Project Kit, catalogue "
           "number 28-247, wood-case version. A self-contained experimenter "
           "board: a fixed set of components mounted to the board with spring "
           "terminals, wired up by hand from the manual's diagrams to make 75 "
           "different circuits.\n\n"
           "ONE UNIT, NOT AN ASSORTMENT. The components are mounted and wired "
           "to the board and are not separately stockable, so this is a single "
           "piece with pack 1 — it is deliberately NOT exploded into component "
           "stock the way a loose assortment kit would be.\n\n"
           "VINTAGE SECONDHAND, bought on eBay from private seller magicamulet "
           f"(item {ITEM_ID}). The listing title says 'NICE!' and states no "
           "condition grade; completeness of the manual, the wire and the "
           "components has NOT been verified. Check what is actually in the "
           "box on arrival before assuming it is complete.\n\n"
           "Created by the queue C daytime sweep, 16:40 run 2026-09-19, from "
           f"eBay order {ORDER}. Category set by precedent with the other "
           "experimenter/breadboard kits in flat Prototyping (#80, #157, #218, "
           "#384); see the script header for what was rejected and why."),
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
    description=f"eBay order {ORDER} — Science Fair 75-in-1 kit (Radio Shack 28-247)",
    issue_date=ISSUE,
    target_date=ARRIVES,
    status=PurchaseOrderStatus.PLACED.value,
    notes=("Auto-created by the queue C daytime sweep, 16:40 run 2026-09-19.\n\n"
           "PRICE SOURCE: the eBay order-confirmation email, which is itemised "
           "and states a per-item price — Price: $25.00, Subtotal $25.00, "
           "Shipping $14.10, Total charged $39.10. The line is booked at the "
           "ITEM price of $25.00. The $39.10 total was NOT used and must not "
           "be: it is 36% shipping on a $25 item, and booking it would inflate "
           "the piece cost by that much forever.\n\n"
           "Best offer accepted by the seller; payment complete.\n\n"
           "Sold by the private eBay seller magicamulet, not by eBay; the "
           "supplier is eBay as the marketplace, per the convention used by "
           "every other marketplace PO here.\n\n"
           "VINTAGE SECONDHAND. No condition grade was stated in the "
           "confirmation and completeness has not been verified — inspect the "
           "kit, the manual and the wire before receiving it.\n\n"
           "TARGET DATE is the LATE end of the quoted delivery range (Thu Sep "
           "24 - Thu Oct 01). Booking the early end would have flagged this "
           "order OVERDUE for a week while it was legitimately in transit.\n\n"
           "PACK: 1 — one kit, one unit.\n\n"
           "PLACED, not received. Receive with receive_po.py when the kit is "
           "physically checked in."),
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
    notes=("Per-item price from the eBay order confirmation: one kit at "
           "$25.00. Shipping of $14.10 is deliberately excluded — the $39.10 "
           "order total is not the item price."))
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
