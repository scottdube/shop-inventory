"""Queue C, 22:40 daytime sweep 2026-10-12: three Amazon orders -> three POs, two parts.

  113-2025058-0925012  placed 2026-10-12, ship to Dover NH, "Arriving tomorrow" (10-13)
    PRIME-LINE Screen & Storm Door Push Button Latch Set, Black, Night Lock
    B002C1RTKY  sold by Amazon.com  $11.86 x1
  113-3566967-2617067  placed 2026-10-12, ship to The Villages FL, "Arriving Thursday" (10-15)
    the same latch set, B002C1RTKY, Amazon.com, $11.86 x1
  113-9765148-4443452  placed 2026-10-12, ship to The Villages FL, "Arriving tomorrow" (10-13)
    Aeotec ZW150 Nano Dimmer Bypass (load resistor / dummy load for TRIAC dimmers)
    B017BK1MIA  sold by Home Controls, Inc.  $16.49 x1

AMAZON PRICE SOURCE -- the order-details pages. All three emails say
"Grand Total: 0.0 USD": the orders were paid with rewards points and gift-card
balance, which is a payment method, not a price. The lines carry the per-item
figures the pages print.

ASINs: the latch title links to B002C1RTKY on the 113-3566967 page; the Dover
order shows the identical title and price, so it is the same listing. B017BK1MIA
is the link whose text is the Aeotec ZW150 title.

Not household consumables (the open amazon-household-subscribe-save decision):
these are hardware, and precedent imports them -- #402 Aeotec Multisensor 6 and
#1133 Prime-Line spring both came in this way. Both will likely be installed
into a building, which makes them deploy_po.py candidates at receive time
(installed infrastructure is not inventory), not reasons to skip the PO.

Categories: latch -> Hardware (136); ZW150 is a line-voltage load device ->
Electrical (71). No IPN, no default_location. PLACED, never received.
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

RUN = "22:40 daytime sweep 2026-10-12"
TODAY = datetime.date(2026, 10, 12)

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

PARTS = {
    "latch": dict(
        asin="B002C1RTKY", cat=136, cat_path="Hardware",
        name="Screen/Storm Door Push-Button Latch Set, black, with night lock",
        desc=("orig: PRIME-LINE Screen & Storm Door Push Button Latch Set, Black, Night Lock; "
              "Amazon B002C1RTKY"),
        kw=("door latch, storm door, screen door, push button latch, handle set, night lock, "
            "door hardware, Prime-Line"),
        sp_desc="PRIME-LINE screen/storm door push-button latch set, black (Amazon.com)",
        notes=("Push-button handle/latch set for a screen or storm door, with an interior "
               "night lock. Counted as ONE set.\n\n"
               "Bought twice on 2026-10-12: one to Dover NH (113-2025058-0925012), one to "
               "The Villages FL (113-3566967-2617067). Likely a house door repair at each "
               "site -- if installed, close the PO with deploy_po.py rather than stocking it."),
        guard=("door latch", "storm door"),
    ),
    "zw150": dict(
        asin="B017BK1MIA", cat=71, cat_path="Electrical",
        name="Dimmer Bypass Load Resistor, Aeotec Nano ZW150 (dummy load for TRIAC dimmers)",
        desc=("orig: Aeotec ZW150 Nano Dimmer Bypass Load Resistor and Dummy Load for Dimmer "
              "TRIAC Dimmer Switches to Fix Flicker Problems - Black; Amazon B017BK1MIA"),
        kw=("dimmer bypass, bypass, load resistor, dummy load, minimum load, LED flicker, "
            "TRIAC dimmer, Z-Wave, Aeotec, ZW150, Nano Bypass"),
        sp_desc="Aeotec ZW150 Nano Dimmer Bypass, black (Home Controls, Inc.)",
        notes=("Adds a minimum load across a light fixture so a no-neutral or TRIAC dimmer "
               "stops flickering/ghosting with low-wattage LED lamps. Wired in parallel with "
               "the lamp, in the fixture or box.\n\n"
               "Ordered 2026-10-12 to The Villages FL (113-9765148-4443452). Will almost "
               "certainly be installed -- close the PO with deploy_po.py when it is."),
        guard=("dimmer bypass", "ZW150"),
    ),
}

ORDERS = [
    dict(order="113-2025058-0925012", part="latch", price="11.86",
         target=datetime.date(2026, 10, 13), ship="Dover NH",
         seller="Amazon.com",
         summary=("Item(s) Subtotal $11.86, shipping $0.00, tax $0.00, Rewards Points "
                  "-$11.86, Grand Total $0.00."),
         what="storm door push-button latch set"),
    dict(order="113-3566967-2617067", part="latch", price="11.86",
         target=datetime.date(2026, 10, 15), ship="The Villages FL",
         seller="Amazon.com",
         summary=("Item(s) Subtotal $11.86, shipping $0.00, tax $0.83, Gift Card Amount "
                  "-$12.69, Grand Total $0.00."),
         what="storm door push-button latch set"),
    dict(order="113-9765148-4443452", part="zw150", price="16.49",
         target=datetime.date(2026, 10, 13), ship="The Villages FL",
         seller="Home Controls, Inc.",
         summary=("Item(s) Subtotal $16.49, shipping $0.00, tax $1.15, Gift Card Amount "
                  "-$6.79, Rewards Points -$10.85, Grand Total $0.00."),
         what="Aeotec ZW150 dimmer bypass"),
]

# ------------------------------------------------------------ checks
for o in ORDERS:
    dup = PurchaseOrder.objects.filter(Q(supplier_reference=o["order"]) | Q(reference=o["order"]))
    if dup.exists():
        sys.exit(f"!! PO already exists for {o['order']}: {[p.reference for p in dup]}")
for key, p in PARTS.items():
    if SupplierPart.objects.filter(SKU__iexact=p["asin"]).exists():
        sys.exit(f"!! supplier part {p['asin']} already exists")
    cat = PartCategory.objects.get(pk=p["cat"])
    assert cat.pathstring == p["cat_path"], cat.pathstring
    assert len(p["kw"]) <= 250 and len(p["name"]) <= 100 and len(p["desc"]) <= 250, \
        (key, len(p["kw"]), len(p["name"]), len(p["desc"]))
    q = Q(name=p["name"]) | Q(description__icontains=p["asin"])
    for g in p["guard"]:
        q |= Q(name__icontains=g) | Q(description__icontains=g)
    hits = Part.objects.filter(q)
    if hits.exists():
        sys.exit(f"!! {key}: a part with this name / ASIN exists: {[h.pk for h in hits]}")
    print(f"{key}: category {cat.pk} {cat.pathstring}, no duplicate")

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ------------------------------------------------------------ parts
made = {}
for key, p in PARTS.items():
    part = Part(name=p["name"], description=p["desc"], category_id=p["cat"], keywords=p["kw"],
                component=False, purchaseable=True, assembly=False,
                notes=p["notes"] + f"\n\nCreated by the queue C daytime sweep, {RUN}.")
    part.save()
    part.refresh_from_db()
    assert part.name == p["name"] and part.category_id == p["cat"] and part.keywords == p["kw"]
    sp = SupplierPart(supplier=amazon, part=part, SKU=p["asin"],
                      link=f"https://www.amazon.com/dp/{p['asin']}", description=p["sp_desc"])
    sp.pack_quantity = "1"
    sp.save()
    sp.refresh_from_db()
    assert sp.SKU == p["asin"] and sp.part_id == part.pk, "sp did not stick"
    made[key] = sp
    print(f"CREATED part #{part.pk} {part.name}  cat={part.category.pathstring}  sp #{sp.pk}")

# ------------------------------------------------------------ POs
for o in ORDERS:
    po = PurchaseOrder(
        supplier=amazon,
        reference=PurchaseOrder.generate_reference(),
        supplier_reference=o["order"],
        description=f"Amazon order {o['order']} — {o['what']} (to {o['ship']})",
        issue_date=TODAY, target_date=o["target"],
        status=PurchaseOrderStatus.PLACED.value,
        notes=(f"Auto-created by the queue C daytime sweep, {RUN}.\n\n"
               f"Ships to {o['ship']}.\n\n"
               f"PRICE SOURCE: the order-details page — ${o['price']} for one {o['what']}, "
               f"sold by {o['seller']}. {o['summary']}\n\n"
               "The $0.00 grand total is cash after rewards points / gift-card balance were "
               "applied as a PAYMENT METHOD. It is not the price and is deliberately not on "
               "the line.\n\nPLACED, not received."),
    )
    po.save()
    po.refresh_from_db()
    assert po.status == PurchaseOrderStatus.PLACED.value
    assert po.supplier_reference == o["order"] and po.reference != o["order"]
    li = PurchaseOrderLineItem(
        order=po, part=made[o["part"]], quantity=1,
        purchase_price=o["price"], purchase_price_currency="USD",
        notes=f"Per-item price from the Amazon order-details page (${o['price']}), NOT the "
              "$0.00 grand total.")
    li.save()
    li.refresh_from_db()
    assert float(li.purchase_price.amount) == float(o["price"]), li.purchase_price
    po.refresh_from_db()
    print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
          f"target={po.target_date} lines={po.lines.count()} @ {li.purchase_price}")
