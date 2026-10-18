"""Queue C, 22:40 daytime sweep 2026-10-17: one Amazon order -> one PO, two lines.

  111-8727063-9233866  placed 2026-10-17, ship to The Villages FL (LRD), "Arriving tomorrow" (10-18)
    1. 10-Pack 10Gbps/120W USB C to USB Adapter & C Male to 3.1 Female Adapter
       B0FQTC76CX  sold by PASTALL       $9.99 x1 (one 10-pack)
    2. Wiha 26390 Screwdriver Set, Hex Metric With Precision Handle, .7 - 3.0mm, 7 Piece
       B0006OBFCC  sold by Wiha Tools    $29.98 x1

AMAZON PRICE SOURCE -- the order-details page: Item(s) Subtotal $39.97 (= 9.99 + 29.98, so
qty 1 each; no quantity badge on either line), shipping $0.00, tax $2.80, rewards points
-$0.34, Grand Total $42.43. The grand total is not a price.

PACKS: the adapter is a 10-pack of identical adapters -> stock counts PIECES, the supplier
part carries pack_quantity 10 (written through .save(), never .update()). The Wiha set is
ONE unit (an assortment of 7 different drivers, not a multipack) -> pack_quantity 1.

Dry run lists existing candidate parts and categories. Pass --part-a / --part-w <pk> to
reuse an existing part, --cat-a / --cat-w <pk> to create. --commit writes. PLACED, never
received.
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

RUN = "22:40 daytime sweep 2026-10-17"
TODAY = datetime.date(2026, 10, 17)
ORDER = "111-8727063-9233866"

LINES = {
    "a": dict(
        asin="B0FQTC76CX", price="9.99", pack="10", seller="PASTALL",
        name="Adapter, USB-C male to USB-A female, 10 Gbps, PASTALL",
        desc=("orig: 10-Pack 10Gbps/120W USB C to USB Adapter & C Male to 3.1 Female Adapter | "
              "Charger Adapter,Two Working Modes,Compatible with MacBook Pro/Air,iPhone 17 16 Pro "
              "Max/15 Plus/14 Samsung Galaxy S25 S24 S23; Amazon B0FQTC76CX"),
        kw=("USB-C, USB C, type-C, USB-A, USB A, adapter, OTG, USB-C male, USB-A female, USB 3.1, "
            "10Gbps, 120W, C to A, PASTALL"),
        sp_desc="PASTALL USB-C male to USB-A female adapter, 10 Gbps, pack of 10",
        notes=("USB-C male plug to USB-A female socket adapter (OTG direction), USB 3.1 10 Gbps, "
               "listing says 120 W. Bought as a 10-pack; stock counts single adapters, the "
               "supplier part carries pack_quantity 10."),
        hits=Q(name__icontains="pastall") | Q(description__icontains="pastall")
             | Q(description__icontains="B0FQTC76CX")
             | (Q(name__icontains="usb") & Q(name__icontains="adapter")),
    ),
    "w": dict(
        asin="B0006OBFCC", price="29.98", pack="1", seller="Wiha Tools",
        name="Hex driver set, precision, metric 0.7-3.0 mm, 7 pc, Wiha 26390",
        desc=("orig: Wiha 26390 Screwdriver Set, Hex Metric With Precision Handle, .7 - 3.0mm, "
              "7 Piece, original version, one size; Amazon B0006OBFCC"),
        kw=("Wiha, 26390, hex driver, hex key, allen, precision screwdriver, metric, 0.7mm, "
            "0.9mm, 1.3mm, 1.5mm, 2mm, 2.5mm, 3mm, screwdriver set, hand tool"),
        sp_desc="Wiha 26390 precision metric hex driver set, 7 pc (Wiha Tools)",
        notes=("Wiha 26390: seven precision hex drivers, metric 0.7-3.0 mm, PicoFinish handles. "
               "One SET (an assortment of different sizes, not a multipack) -> pack_quantity 1."),
        hits=Q(name__icontains="wiha") | Q(description__icontains="wiha")
             | Q(description__icontains="B0006OBFCC") | Q(name__icontains="26390")
             | (Q(name__icontains="hex") & (Q(name__icontains="driver") | Q(name__icontains="key"))),
    ),
}

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--cat-a", type=int)
ap.add_argument("--cat-w", type=int)
ap.add_argument("--part-a", type=int)
ap.add_argument("--part-w", type=int)
args = ap.parse_args()
choice = {"a": (args.cat_a, args.part_a), "w": (args.cat_w, args.part_w)}

amazon = Company.objects.get(name="Amazon")

# ------------------------------------------------------------ checks
dup = PurchaseOrder.objects.filter(Q(supplier_reference=ORDER) | Q(reference=ORDER))
if dup.exists():
    sys.exit(f"!! PO already exists for {ORDER}: {[p.reference for p in dup]}")
for k, L in LINES.items():
    assert len(L["kw"]) <= 250 and len(L["name"]) <= 100 and len(L["desc"]) <= 250, \
        (k, len(L["kw"]), len(L["name"]), len(L["desc"]))
    print(f"--- line {k}: {L['name']}")
    sp = SupplierPart.objects.filter(SKU__iexact=L["asin"]).first()
    if sp:
        print(f"  supplier part {L['asin']} already exists: sp #{sp.pk} -> part #{sp.part_id}")
    for h in Part.objects.filter(L["hits"])[:40]:
        print(f"  candidate part #{h.pk}: {h.name}  active={h.active}  cat={h.category_id}: {h.category}")

print("categories:")
for c in PartCategory.objects.filter(Q(name__icontains="cable") | Q(name__icontains="usb")
                                     | Q(name__icontains="adapter") | Q(name__icontains="tool")
                                     | Q(name__icontains="driver") | Q(name__icontains="hand")
                                     | Q(name__icontains="interface")):
    print(f"  {c.pk}: {c.pathstring}  ({c.parts.count()} parts)")

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --cat-a/--cat-w <pk> (or --part-a/--part-w <pk>) --commit")

# ------------------------------------------------------------ parts
sps = {}
for k, L in LINES.items():
    cat_pk, part_pk = choice[k]
    sp = SupplierPart.objects.filter(SKU__iexact=L["asin"]).first()
    if sp:
        print(f"REUSING sp #{sp.pk} part #{sp.part_id}")
        sps[k] = sp
        continue
    if part_pk:
        part = Part.objects.get(pk=part_pk)
        print(f"REUSING part #{part.pk} {part.name}")
    else:
        assert cat_pk, f"line {k}: need --cat-{k} or --part-{k}"
        cat = PartCategory.objects.get(pk=cat_pk)
        part = Part(name=L["name"], description=L["desc"], category=cat, keywords=L["kw"],
                    component=False, purchaseable=True, assembly=False,
                    notes=L["notes"] + f"\n\nOrdered 2026-10-17 to The Villages FL (LRD), "
                          f"Amazon {ORDER}.\n\nCreated by the queue C daytime sweep, {RUN}.")
        part.save()
        part.refresh_from_db()
        assert part.name == L["name"] and part.category_id == cat.pk and part.keywords == L["kw"]
        print(f"CREATED part #{part.pk} {part.name}  cat={part.category.pathstring}")
    sp = SupplierPart(supplier=amazon, part=part, SKU=L["asin"],
                      link=f"https://www.amazon.com/dp/{L['asin']}", description=L["sp_desc"])
    sp.pack_quantity = L["pack"]
    sp.save()
    sp.refresh_from_db()
    assert sp.SKU == L["asin"] and sp.part_id == part.pk, "sp did not stick"
    assert float(sp.pack_quantity_native) == float(L["pack"]), \
        f"pack native {sp.pack_quantity_native} != {L['pack']}"
    print(f"  sp #{sp.pk}  pack_quantity={sp.pack_quantity} native={sp.pack_quantity_native}")
    sps[k] = sp

# ------------------------------------------------------------ PO
po = PurchaseOrder(
    supplier=amazon,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=f"Amazon order {ORDER} — USB-C to USB-A adapters (10-pk) + Wiha 26390 hex set (to The Villages FL)",
    issue_date=TODAY, target_date=datetime.date(2026, 10, 18),
    status=PurchaseOrderStatus.PLACED.value,
    notes=(f"Auto-created by the queue C daytime sweep, {RUN}.\n\n"
           "Ships to The Villages FL (LRD).\n\n"
           "PRICE SOURCE: the order-details page — $9.99 for one 10-pack of PASTALL USB-C to "
           "USB-A adapters, $29.98 for one Wiha 26390 set. Item(s) Subtotal $39.97, shipping "
           "$0.00, tax $2.80, rewards points -$0.34, Grand Total $42.43.\n\n"
           "The $42.43 grand total includes tax and points; it is not a price and is "
           "deliberately not on any line.\n\nPLACED, not received."),
)
po.save()
po.refresh_from_db()
assert po.status == PurchaseOrderStatus.PLACED.value
assert po.supplier_reference == ORDER and po.reference != ORDER
for k, L in LINES.items():
    li = PurchaseOrderLineItem(
        order=po, part=sps[k], quantity=1,
        purchase_price=L["price"], purchase_price_currency="USD",
        notes=f"Per-item price from the Amazon order-details page (${L['price']}, sold by "
              f"{L['seller']}), NOT the $42.43 grand total."
              + (" Quantity 1 = one 10-pack." if L["pack"] != "1" else ""))
    li.save()
    li.refresh_from_db()
    assert float(li.purchase_price.amount) == float(L["price"]), li.purchase_price
    print(f"  line {k}: sp #{sps[k].pk} qty {li.quantity} @ {li.purchase_price}")
po.refresh_from_db()
print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
      f"target={po.target_date} lines={po.lines.count()}")
