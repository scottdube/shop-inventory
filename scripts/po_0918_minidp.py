"""Queue C: Amazon order 113-9362952-1785800 (2026-09-18) -> new part + PO.

biaze 8K Mini DisplayPort to DisplayPort 1.4 adapter, ASIN B0FH6L2HJR, sold by
biaze, shipped by Amazon. ONE 2-PACK, arriving 2026-09-19.

PRICE SOURCE -- the order-details page, per item:

    biaze 8K Mini DisplayPort to DisplayPort 1.4 Adapter 2 Pack
    Sold by: biaze                                        $16.99

**Booked at $16.99 for the pack. The order list says Grand Total $0.00.**
That number is worth nothing here and is exactly the case the standing rule was
written for: the page reads Item(s) Subtotal $16.99, Shipping $0.00, tax $0.00,
Gift Card Amount -$16.99, Grand Total $0.00. A gift-card balance is a payment
instrument, not a discount -- these adapters cost nothing out of pocket and are
still a $16.99 asset. Booking $0.00 would have put free adapters on the books.
This is the second time in one day the same trap fired on this account; PO-0175
(UniFi nanoHD, 16:40 run) was the first.

PACK: **2, not 1.** This is a genuine multipack of two identical adapters, not
an assortment, so the 480-piece-kit exception does not apply. It is not a
judgement call either -- the listing page states the unit price itself:

    $16.99   ($8.50 per count)

so Amazon and this record agree that a piece costs $8.50. Setting the pack at
creation is transcription, NOT the costing decision that the open
`zip-bag-pack-quantity-400-vs-1` item is holding: that one asks about CHANGING
three existing supplier parts whose prices are already booked against a wrong
pack, and this part has no history to move. CLAUDE.md's standing complaint --
"we seem to have this problem every time we buy something that comes in a
multipack", 688 of 706 supplier parts wrong -- is caused precisely by importers
never asking the question at creation. Asked and answered.

CATEGORY: `Electronics/Cables` (pk 119) by sibling precedent, not by taste.
Two video adapters of the same family already live there -- #1198 "Adapter
Cable, DisplayPort male to Mini-HDMI male" and #1145 "Adapter Cable, micro-HDMI
male to HDMI female". `Electronics/Connectors/Adapters` (pk 127) was rejected
after looking at what is actually in it: a bare nRF24L01 socket adapter PLATE
and a USB-C right-angle shell, i.e. passive connector adapters, not video
signalling. The video adapters cluster in Cables and this joins them.

IDENTITY, read off the listing rather than guessed from the title: this is a
short dongle, not a cable run. Mini DisplayPort MALE plugs into the source
(Thunderbolt 2 / Mini DP port); the far end is a full-size DisplayPort FEMALE
socket that a separate DP cable plugs into -- "then connected to a monitor with
a DisplayPort input via a separate DisplayPort cable". It is UNIDIRECTIONAL:
source -> display only. That direction is on the part notes because it is the
one way to own this part and still have it not work.

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

ORDER = "113-9362952-1785800"
ISSUE = datetime.date(2026, 9, 18)
ARRIVES = datetime.date(2026, 9, 19)
SUBTOTAL = 16.99

ASIN = "B0FH6L2HJR"
UNIT = "16.99"          # price of ONE PACK; pack_quantity 2 -> $8.50 a piece
QTY = 1                 # one pack ordered
PACK = "2"

NAME = ("Adapter, Mini DisplayPort male to DisplayPort female, 8K@60Hz, "
        "DP 1.4, unidirectional")
DESC = ("orig: biaze 8K Mini DisplayPort to DisplayPort 1.4 Adapter 2 Pack | "
        "32.4Gbps 8K@60Hz Unidirectional Mini DP to DP Converter for Gaming "
        "Laptop, MacBook, iMac, Monitor, VR")
KEYWORDS = ("Mini DisplayPort, mini DP, mDP, Thunderbolt 2, DisplayPort, DP, "
            "DP 1.4, adapter, converter, dongle, male to female, video "
            "adapter, 8K60, 4K120, 4K144, 32.4Gbps, HBR3, unidirectional, "
            "biaze, monitor, multi-monitor, MacBook, Surface")

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
dupes = (Part.objects.filter(name__icontains="DisplayPort")
         | Part.objects.filter(name__icontains="Mini DP")
         | Part.objects.filter(name__icontains="biaze")
         | Part.objects.filter(IPN=ASIN)
         | Part.objects.filter(description__icontains=ASIN)
         | Part.objects.filter(description__icontains="biaze")).distinct()
for d in dupes:
    print(f"  possible dupe: #{d.pk} active={d.active} {d.name}")
if SupplierPart.objects.filter(supplier=amazon, SKU=ASIN).exists():
    sys.exit(f"!! supplier part {ASIN} already exists — resolve by hand")

total = float(UNIT) * QTY
print(f"reconcile: lines sum {total:.2f} vs page subtotal {SUBTOTAL:.2f}")
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
cat = PartCategory.objects.get(pk=119)
assert cat.pathstring == "Electronics/Cables", f"category moved: {cat.pathstring}"
part = Part(
    name=NAME,
    description=DESC,
    category=cat,
    IPN=ASIN,
    keywords=KEYWORDS,
    component=True,
    purchaseable=True,
    assembly=False,
    units="",
    notes=("Short adapter dongle, NOT a cable run. Mini DisplayPort MALE plugs "
           "into the source — a Thunderbolt 2 / Mini DP output on a laptop or "
           "a graphics card — and the far end is a full-size DisplayPort "
           "FEMALE socket. A separate DisplayPort cable runs from there to the "
           "monitor; this adapter does not reach a display on its own.\n\n"
           "**UNIDIRECTIONAL: source -> display only.** It will not carry a DP "
           "source into a Mini DP input. This is the one way to own the part "
           "and still have nothing on screen, and the listing's own 1-star "
           "review is somebody who wired it backwards.\n\n"
           "DP 1.4 / HBR3, 32.4 Gbit/s: 8K@60Hz, 4K@120Hz, 4K@144Hz, "
           "2K@165Hz. Carries audio as well as video (7.1 / 5.1 / 2-channel "
           "uncompressed pass-through). Gold-plated contacts, braided jacket, "
           "aluminium shell. Passive — no drivers, no external power.\n\n"
           "BOUGHT AS A 2-PACK; stock counts PIECES, so one pack received is "
           "2 pieces. The supplier part carries pack_quantity 2 and Amazon's "
           "own listing agrees at $8.50 per count.\n\n"
           "LIKELY RELATED, recorded as an observation and not as fact: eBay "
           "order 06-15193-19595, placed the same day about two hours later, "
           "is an NVIDIA T400 whose three outputs are all Mini DisplayPort "
           "(part created alongside this one). A pair of mDP adapters and a "
           "3x mDP card on the same day read as one multi-monitor build, but "
           "nobody said so and no project link has been made.\n\n"
           "Created by the queue C daytime sweep, 22:40 run 2026-09-18, from "
           f"Amazon order {ORDER}. Category set by precedent with #1198 and "
           "#1145, the other video adapters in Electronics/Cables."),
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
      f"native={sp.pack_quantity_native}  -> "
      f"${float(UNIT) / float(PACK):.2f} a piece")

# ---------------------------------------------------------------- PO
po = PurchaseOrder(
    supplier=amazon,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=f"Amazon order {ORDER} — Mini DP to DP 1.4 adapter, 2-pack",
    issue_date=ISSUE,
    target_date=ARRIVES,
    status=PurchaseOrderStatus.PLACED.value,
    notes=("Auto-created by the queue C daytime sweep, 22:40 run 2026-09-18.\n\n"
           "PRICE SOURCE: the order-details page, per item — $16.99 for the "
           "2-pack.\n\n"
           "THE GRAND TOTAL ON THIS ORDER IS $0.00 AND IS NOT THE PRICE. The "
           "page reads Item(s) Subtotal $16.99, Shipping & Handling $0.00, "
           "tax $0.00, Gift Card Amount -$16.99, Grand Total $0.00. A "
           "gift-card balance is a payment instrument, not a discount; the "
           "adapters are a $16.99 asset that happened to cost nothing out of "
           "pocket. Second time today — PO-0175 was the first.\n\n"
           "PACK: 2. One pack ordered = 2 pieces of stock at $8.50 each, and "
           "the listing states $8.50 per count independently. Receiving this "
           "order with receive_po.py will book 2 pieces, not 1.\n\n"
           "Sold by the marketplace seller \"biaze\" and shipped by Amazon; "
           "the supplier is Amazon as the marketplace, per the convention used "
           "by every other marketplace PO here.\n\n"
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
    notes=("Per-item price from the Amazon order-details page: one 2-pack at "
           "$16.99. The Grand Total is $0.00 because a $16.99 gift-card "
           "balance paid for it — payment method, not price. Pack is 2, so "
           "this receives as 2 pieces at $8.50 each."))
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
