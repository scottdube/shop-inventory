"""Queue C: eBay order 06-15193-19595 (2026-09-18) -> new part + PO.

NVIDIA T400 4GB GDDR6 low-profile workstation GPU with 3x Mini DisplayPort,
eBay item 398401022842, seller paz.salez_17. One unit.

PRICE SOURCE -- the eBay order-confirmation email, which is itemised and states
the per-item price directly:

    Price: $118.00
    Subtotal   $118.00
    Shipping   Free
    Total charged to x -7953   $118.00

Booked at $118.00. Nothing to divide: eBay quotes a unit price for a single
item, and shipping is free, so the line total and the order total agree exactly.
The assert at the bottom is what proves it rather than my saying so.

SUPPLIER: eBay (Company #14), SKU = the eBay ITEM id, link = /itm/<item id>.
That is the convention already set by the only two eBay supplier parts in the
system -- sp #536 (SKU 221473038845, link https://www.ebay.com/itm/221473038845)
and sp #686 (SKU 274721624359). The ORDER number goes in supplier_reference
only, matching PO-0135 (supplier_reference '11-11666-54508'). The seller is a
private eBay account, not a Company -- same marketplace convention as Amazon.

CATEGORY: flat `Modules` (pk 22) by precedent, not by taste. There is no
computer/PC-hardware category anywhere in this instance -- checked the whole
tree (cat_probe_0918_2240.py). The nearest real siblings are board-level
computer assemblies which all sit in flat Modules: #395 Vilros Raspberry Pi 4
starter kit, #350 Pi 4 official PSU. `Electronics/Modules/Video` (pk 124) was
rejected: it is one of the documented Electronics shadow roots, holds exactly
one part, and the flat side usually wins here. I did NOT create a `Computers`
category -- 14 shadow roots are already open and adding a root on my own
judgement during an unattended run is a taxonomy decision, not transcription.
If more PC hardware lands, that becomes a real question worth asking.

PACK: 1. A single card, not a multipack -- checked, because 688 of 706 supplier
parts once carried a wrong pack.

TARGET DATE: the email gives a RANGE, Wed Sep 23 - Tue Sep 29. Booked as the
LATE end (2026-09-29) so the order does not read OVERDUE on the purchasing
screen for the six days it is legitimately still in transit.

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

ORDER = "06-15193-19595"
ISSUE = datetime.date(2026, 9, 18)
ARRIVES = datetime.date(2026, 9, 29)          # late end of the quoted range
SUBTOTAL = 118.00

ITEM_ID = "398401022842"
UNIT = "118.00"
QTY = 1
PACK = "1"

NAME = "NVIDIA T400 4GB GDDR6 Graphics Card, Low Profile, 3x Mini DisplayPort"
DESC = "orig: NVIDIA T400 4GB GDDR6 Low Profile GPU 3x Mini DisplayPort"
KEYWORDS = ("NVIDIA, T400, Quadro, GPU, graphics card, video card, GDDR6, "
            "4GB, low profile, half height, PCIe, PCI Express, x16, "
            "Mini DisplayPort, mDP, mini DP, multi-monitor, triple head, "
            "workstation, Turing, TU117")

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
dupes = (Part.objects.filter(name__icontains="T400")
         | Part.objects.filter(name__icontains="nvidia")
         | Part.objects.filter(name__icontains="graphics card")
         | Part.objects.filter(name__icontains="GPU")
         | Part.objects.filter(IPN=ITEM_ID)
         | Part.objects.filter(description__icontains="GDDR")).distinct()
for d in dupes:
    print(f"  possible dupe: #{d.pk} active={d.active} {d.name}")
if SupplierPart.objects.filter(supplier=ebay, SKU=ITEM_ID).exists():
    sys.exit(f"!! supplier part {ITEM_ID} already exists — resolve by hand")

total = float(UNIT) * QTY
print(f"reconcile: lines sum {total:.2f} vs email subtotal {SUBTOTAL:.2f}")
assert abs(total - SUBTOTAL) < 0.005, "line price does not reconcile — refusing"

# Part.keywords is capped at 250 chars. Checked HERE, before the dry-run exit,
# so an over-length list fails the dry run instead of blowing up mid-commit
# after the reconcile has already passed — which is how it first bit, 2026-09-18.
print(f"keywords: {len(KEYWORDS)} chars (limit 250)")
assert len(KEYWORDS) <= 250, f"keywords too long: {len(KEYWORDS)}"
assert len(NAME) <= 100, f"name too long: {len(NAME)}"

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ---------------------------------------------------------------- part
cat = PartCategory.objects.get(pk=22)
assert cat.pathstring == "Modules", f"category moved: {cat.pathstring}"
part = Part(
    name=NAME,
    description=DESC,
    category=cat,
    IPN=ITEM_ID,
    keywords=KEYWORDS,
    component=True,
    purchaseable=True,
    assembly=False,
    notes=("NVIDIA T400 4GB: single-slot, low-profile PCI Express workstation "
           "graphics card on the Turing TU117 die, 4GB GDDR6. Three Mini "
           "DisplayPort outputs, so it drives three displays from one slot — "
           "which is the whole point of the card in a small chassis.\n\n"
           "EACH OUTPUT IS MINI DisplayPort, NOT full-size DP. Anything "
           "plugged into this card needs a Mini DP adapter or a Mini DP cable; "
           "a standard DisplayPort cable does not fit.\n\n"
           "Bought used/secondhand on eBay from private seller paz.salez_17 "
           "(item 398401022842). Condition was not stated in the order "
           "confirmation and has NOT been verified — check the card on arrival "
           "before assuming it is new.\n\n"
           "LIKELY RELATED, recorded as an observation and not as fact: Amazon "
           "order 113-9362952-1785800, placed the same day about two hours "
           "earlier, is a 2-pack of Mini DisplayPort to DisplayPort adapters "
           "(part created alongside this one). Three mDP outputs and a pair of "
           "mDP adapters on the same day read as one multi-monitor build, but "
           "nobody said so and no project link has been made.\n\n"
           "Created by the queue C daytime sweep, 22:40 run 2026-09-18, from "
           f"eBay order {ORDER}. Category set by precedent with #395 and #350, "
           "the other board-level computer assemblies in flat Modules; this "
           "instance has no computer/PC-hardware category."),
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
    description=f"eBay order {ORDER} — NVIDIA T400 4GB low-profile GPU",
    issue_date=ISSUE,
    target_date=ARRIVES,
    status=PurchaseOrderStatus.PLACED.value,
    notes=("Auto-created by the queue C daytime sweep, 22:40 run 2026-09-18.\n\n"
           "PRICE SOURCE: the eBay order-confirmation email, which is itemised "
           "and states a per-item price — Price: $118.00, Subtotal $118.00, "
           "Shipping Free, Total charged $118.00. Nothing was divided or "
           "derived; the line and the order total agree exactly.\n\n"
           "Sold by the private eBay seller paz.salez_17, not by eBay; the "
           "supplier is eBay as the marketplace, per the convention used by "
           "every other marketplace PO here (and by PO-0135).\n\n"
           "USED/SECONDHAND. Condition was not stated in the confirmation and "
           "has not been verified — inspect the card before receiving it.\n\n"
           "TARGET DATE is the LATE end of the quoted delivery range (Wed Sep "
           "23 - Tue Sep 29). Booking the early end would have flagged this "
           "order OVERDUE for six days while it was legitimately in transit.\n\n"
           "PACK: 1 — a single card.\n\n"
           "PLACED, not received. Receive with receive_po.py when the card is "
           "physically checked in and inspected."),
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
    notes=("Per-item price from the eBay order confirmation: one card at "
           "$118.00, shipping free. Not derived from an order total."))
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
