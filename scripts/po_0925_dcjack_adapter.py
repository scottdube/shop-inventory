"""Queue C, 22:40 sweep 2026-09-25: two Amazon orders -> two new parts + two POs.

  113-3662169-9294634  DIYhz 20 Pack 5.5 x 2.1 mm DC power jack, panel mount
                       ASIN B08CVCJ97Q, sold by DIYhz, one pack at $7.99
  113-0031489-9794658  UL Listed 12V 2A 24W AC/DC power supply adapter, 5 pack
                       ASIN B0DKT5DH2K, sold by Wefomey-US, one pack at $27.99

ASINs were read off the product anchor whose text is the ordered item's title
on each order-details page -- the page also carries ~25 recommendation anchors,
so "first /dp/ link on the page" would have been wrong.

PRICE SOURCE -- the order-details page, per item:

    DC jack:  Item(s) Subtotal $7.99,  shipping 0, tax 0, Grand Total $7.99
    Adapter:  Item(s) Subtotal $27.99, shipping 0, tax 0,
              Rewards Points -$9.75,   Grand Total $18.24

**The adapter is booked at $27.99, not the $18.24 the email says.** 975 Amazon
Visa reward points paid $9.75 of it -- a payment instrument, not a discount.
Same shape as PO-0175 (nanoHD) and the EC11 encoders (gift card); decided there.

DUPLICATE SCAN (probe_0925_2240.py): neither ASIN exists as SKU, IPN or in a
description. Nearest rows, and why they are different parts:
  - #1200 DC Barrel Pigtail 5.5 x 2.1 FEMALE, flying leads -- a pigtail on
    leads, not a chassis socket. Different object, different use.
  - #1218 PS-009 12V 1.5A, #1102 12V 3A -- different current ratings.

PACK IS WRITTEN HERE because these are NEW supplier parts and the title states
it ("20 Pack", "5 Pack"). The EC11 script refused to write a pack because it
would have CHANGED an existing supplier part -- a costing call. Leaving a new
one at InvenTree's default of 1 is exactly the 688-of-706 bug in CLAUDE.md.
The PO line is one pack at the pack price (a PO line is denominated per
supplier unit), so receive_po.py books 20 jacks at $0.40 and 5 adapters at
$5.60.

CATEGORY by precedent: the jack goes with the other chassis/board connectors in
flat `Connectors` (IDC sockets #1251, #1252); the adapter with every other wall
adapter in `Electronics/Power` (#1102, #1217-#1219, #1225, #1237). Flat `Power`
was rejected: it holds motor speed controllers, not supplies.

NOT RECORDED because the order line does not say it: the adapter's barrel size
and polarity. 5.5 x 2.1 C+ is the likely answer and is exactly what must not
be written down unmeasured -- read it off the nameplate at check-in.

No image (image work belongs to the 02:05 job). No default_location (none is
known yet; it is set when a spare goes home). PLACED, never received.
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

ISSUE = datetime.date(2026, 9, 25)
ARRIVES = datetime.date(2026, 9, 26)      # both pages: "Arriving tomorrow"
RUN = "22:40 run 2026-09-25"

ORDERS = [
    dict(
        order="113-3662169-9294634",
        asin="B08CVCJ97Q",
        seller="DIYhz",
        unit="7.99", qty=1, pack="20", subtotal=7.99, grand=7.99,
        cat="Connectors",
        name="DC Barrel Jack, 5.5 x 2.1 mm FEMALE, panel mount, 2-pin",
        desc=("orig: DIYhz 20 Pack 5.5mm x 2.1mm DC Power Jack, 24V 4A 2 Pin "
              "Panel Mount Socket for Router CCTV LED Strip Small Electronics"),
        keywords=("DC jack, DC power jack, barrel jack, barrel socket, 5.5x2.1, "
                  "5.5 x 2.1 mm, 2.1mm, panel mount, chassis mount, female, "
                  "DC socket, power input, 12V, 24V, 4A, DIYhz, DC-022"),
        notes=("Female 5.5 x 2.1 mm DC barrel socket for panel mounting, 2 pins. "
               "Listing rating 24 V 4 A. Takes the male plug of a wall adapter "
               "through an enclosure wall.\n\n"
               "NOT the same part as #1200 (the same socket on flying leads).\n\n"
               "The 'DC-022' keyword is a search aid for the common style name, "
               "NOT an identity claim -- the listing gives no model number. "
               "Thread size, nut and panel-hole diameter NOT recorded: read them "
               "off the part at check-in.\n\n"
               "Pack: 20 per Amazon unit (supplier fact, on the supplier part)."),
        po_desc="DC barrel jacks 5.5 x 2.1, panel mount (20-pack)",
        price_note=("Item(s) Subtotal $7.99, shipping $0.00, tax $0.00, Grand "
                    "Total $7.99 -- no rewards or gift card on this order."),
    ),
    dict(
        order="113-0031489-9794658",
        asin="B0DKT5DH2K",
        seller="Wefomey-US",
        unit="27.99", qty=1, pack="5", subtotal=27.99, grand=18.24,
        cat="Electronics/Power",
        name="Power Adapter 12V 2A (24W), UL listed",
        desc="orig: UL Listed 12V 2A 24W AC DC Power Supply Adapter, 5 Pack",
        keywords=("power adapter, wall adapter, wall wart, power supply, PSU, "
                  "AC DC adapter, 12V, 12 V, 2A, 24W, 12V 2A, UL listed, "
                  "barrel plug, DC plug, Wefomey"),
        notes=("Mains wall adapter, 12 V DC 2 A (24 W) out, UL listed per the "
               "listing.\n\n"
               "BARREL SIZE AND POLARITY NOT RECORDED -- the order line does not "
               "state them. Read the nameplate at check-in and add them to the "
               "name the way PS-009 carries '5.5x2.1 C+'.\n\n"
               "Pack: 5 per Amazon unit (supplier fact, on the supplier part)."),
        po_desc="12V 2A wall adapters (5-pack)",
        price_note=("Item(s) Subtotal $27.99, shipping $0.00, tax $0.00, Rewards "
                    "Points -$9.75, Grand Total $18.24. THE $18.24 IS NOT THE "
                    "PRICE: 975 Amazon Visa reward points paid $9.75 of it, a "
                    "payment instrument, not a discount. Same shape as PO-0175 "
                    "(nanoHD) and the EC11 encoders, decided there."),
    ),
]

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

# ------------------------------------------------------------ checks, all rows
for o in ORDERS:
    print(f"\n=== {o['order']}  {o['name']}")
    dup_po = PurchaseOrder.objects.filter(
        Q(supplier_reference=o["order"]) | Q(reference=o["order"]))
    if dup_po.exists():
        sys.exit(f"!! PO already exists for {o['order']}: "
                 f"{[p.reference for p in dup_po]} — nothing to do")
    if SupplierPart.objects.filter(SKU__iexact=o["asin"]).exists():
        sys.exit(f"!! supplier part {o['asin']} already exists — resolve by hand")
    if Part.objects.filter(Q(IPN__iexact=o["asin"]) | Q(name=o["name"])).exists():
        sys.exit(f"!! a part with IPN {o['asin']} or this exact name exists")
    total = float(o["unit"]) * o["qty"]
    print(f"  reconcile: line {total:.2f} vs page subtotal {o['subtotal']:.2f} "
          f"(grand total {o['grand']:.2f})")
    assert abs(total - o["subtotal"]) < 0.005, "line does not reconcile — refusing"
    assert len(o["keywords"]) <= 250, f"keywords too long: {len(o['keywords'])}"
    assert len(o["name"]) <= 100, f"name too long: {len(o['name'])}"
    cats = [c for c in PartCategory.objects.filter(name=o["cat"].split("/")[-1])
            if c.pathstring == o["cat"]]
    assert len(cats) == 1, f"category {o['cat']} not unique: {cats}"
    o["cat_obj"] = cats[0]
    print(f"  category pk {cats[0].pk} {cats[0].pathstring} "
          f"({cats[0].parts.count()} parts)  pack {o['pack']}  "
          f"per piece ${float(o['unit']) / float(o['pack']):.4f}")

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ------------------------------------------------------------------- writes
for o in ORDERS:
    part = Part(
        name=o["name"], description=o["desc"], category=o["cat_obj"],
        IPN=o["asin"], keywords=o["keywords"],
        component=True, purchaseable=True, assembly=False,
        notes=(o["notes"] + f"\n\nCreated by the queue C daytime sweep, {RUN}, "
               f"from Amazon order {o['order']} (sold by {o['seller']})."),
    )
    part.save()
    part.refresh_from_db()
    assert part.name == o["name"] and part.IPN == o["asin"], "part did not stick"
    assert part.category_id == o["cat_obj"].pk, "category did not stick"
    assert part.keywords == o["keywords"], "keywords did not stick"
    print(f"\nCREATED part #{part.pk} {part.name}  cat={part.category.pathstring}")

    sp = SupplierPart(supplier=amazon, part=part, SKU=o["asin"],
                      link=f"https://www.amazon.com/dp/{o['asin']}")
    sp.pack_quantity = o["pack"]      # .save() -> clean() -> pack_quantity_native
    sp.save()
    sp.refresh_from_db()
    assert float(sp.pack_quantity_native) == float(o["pack"]), \
        f"pack_quantity_native did not stick: {sp.pack_quantity_native}"
    print(f"  sp #{sp.pk} SKU={sp.SKU} pack={sp.pack_quantity} "
          f"native={sp.pack_quantity_native}")

    po = PurchaseOrder(
        supplier=amazon,
        reference=PurchaseOrder.generate_reference(),
        supplier_reference=o["order"],
        description=f"Amazon order {o['order']} — {o['po_desc']}",
        issue_date=ISSUE, target_date=ARRIVES,
        status=PurchaseOrderStatus.PLACED.value,
        notes=(f"Auto-created by the queue C daytime sweep, {RUN}.\n\n"
               f"PRICE SOURCE: the order-details page, per item — ${o['unit']} "
               f"for one {o['pack']}-pack. {o['price_note']}\n\n"
               f"NEW PART #{part.pk}; no duplicate by ASIN, IPN, name or "
               f"description. Sold by the marketplace seller \"{o['seller']}\"; "
               "the supplier is Amazon as the marketplace, per convention.\n\n"
               "PLACED, not received. Receive with receive_po.py when the box "
               "is physically checked in."),
    )
    po.save()
    po.refresh_from_db()
    assert po.status == PurchaseOrderStatus.PLACED.value, "PO status did not stick"
    assert po.supplier_reference == o["order"], "supplier_reference did not stick"
    assert po.reference != o["order"], "vendor number leaked into reference"

    li = PurchaseOrderLineItem(
        order=po, part=sp, quantity=o["qty"],
        purchase_price=o["unit"], purchase_price_currency="USD",
        notes=f"Per-item price from the Amazon order-details page: one "
              f"{o['pack']}-pack at ${o['unit']}.")
    li.save()
    li.refresh_from_db()
    assert float(li.purchase_price.amount) == float(o["unit"]), \
        f"price did not stick: {li.purchase_price}"
    booked = sum(float(l.purchase_price.amount) * float(l.quantity)
                 for l in po.lines.all())
    assert abs(booked - o["subtotal"]) < 0.005, "booked total drifted from the page"
    print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} "
          f"line qty {li.quantity} @ {li.purchase_price}  booked ${booked:.2f}")
