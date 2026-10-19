"""Queue C, 22:40 daytime sweep 2026-10-18: one Amazon order -> one PO, one line.

  113-2965388-1706666  placed 2026-10-18, ship to The Villages FL (LRD), "Arriving tomorrow" (10-19)
    1. Hollyland Lark M2 Wireless Microphone (2TX + 3RX + Charging Case)
                                        B0CP7QXWPN  sold by Hollyland Official Store  $99.00 x1

AMAZON PRICE SOURCE -- the order-details page: Item(s) Subtotal $99.00 (one line, no quantity
badge, so qty 1), shipping $0.00, tax $6.93, Grand Total $105.93. The grand total is not a price.

PACK: one system (two transmitters, three receivers and a charging case) -- an assortment, not a
multipack of interchangeable pieces -> pack_quantity 1.

Dry run lists existing candidate parts and categories. Pass --part <pk> to reuse an existing
part, --cat <pk> to create. --commit writes. PLACED, never received.
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

RUN = "22:40 daytime sweep 2026-10-18"
TODAY = datetime.date(2026, 10, 18)
ORDER = "113-2965388-1706666"

L = dict(
    asin="B0CP7QXWPN", price="99.00", pack="1", seller="Hollyland Official Store",
    name="Microphone kit, wireless, Hollyland Lark M2, 2 TX + 3 RX + charging case",
    desc=("orig: Hollyland Lark M2 Wireless Microphone for iPhone/Camera/Android/PC, 48kHz/24-bit "
          "High Fidelity Audio, 300m Range, Noise Cancelling, 40h Use, YouTube, Vlog, Streaming "
          "(2TX + 3RX + Charging Case); Amazon B0CP7QXWPN"),
    kw=("microphone, mic, wireless, wireless mic, lavalier, lav, Lark M2, Hollyland, transmitter, "
        "receiver, USB-C, Lightning, 3.5mm, camera, video, recording, podcast, charging case"),
    sp_desc="Hollyland Lark M2 wireless mic kit, 2 TX + 3 RX + charging case",
    notes=("Hollyland Lark M2 wireless microphone system: two clip-on transmitters, three "
           "receivers (listing: for iPhone, camera, Android/PC) and a charging case; 48 kHz / "
           "24-bit, 300 m range, noise cancelling, 40 h with case. One KIT (not a multipack of "
           "interchangeable pieces) -> pack_quantity 1."),
    hits=Q(name__icontains="hollyland") | Q(description__icontains="hollyland")
         | Q(description__icontains="B0CP7QXWPN") | Q(name__icontains="lark")
         | Q(name__icontains="microphone"),
)

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
assert len(L["kw"]) <= 250 and len(L["name"]) <= 100 and len(L["desc"]) <= 250, \
    (len(L["kw"]), len(L["name"]), len(L["desc"]))
print(f"--- line: {L['name']}")
sp = SupplierPart.objects.filter(SKU__iexact=L["asin"]).first()
if sp:
    print(f"  supplier part {L['asin']} already exists: sp #{sp.pk} -> part #{sp.part_id}")
for h in Part.objects.filter(L["hits"])[:40]:
    print(f"  candidate part #{h.pk}: {h.name}  active={h.active}  cat={h.category_id}: {h.category}")

print("categories:")
for c in PartCategory.objects.filter(Q(name__icontains="audio") | Q(name__icontains="video")
                                     | Q(name__icontains="camera") | Q(name__icontains="micro")
                                     | Q(name__icontains="media") | Q(name__icontains="photo")):
    print(f"  {c.pk}: {c.pathstring}  ({c.parts.count()} parts)")

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --cat <pk> (or --part <pk>) --commit")

# ------------------------------------------------------------ part
if sp:
    print(f"REUSING sp #{sp.pk} part #{sp.part_id}")
else:
    if args.part:
        part = Part.objects.get(pk=args.part)
        print(f"REUSING part #{part.pk} {part.name}")
    else:
        assert args.cat, "need --cat or --part"
        cat = PartCategory.objects.get(pk=args.cat)
        part = Part(name=L["name"], description=L["desc"], category=cat, keywords=L["kw"],
                    component=False, purchaseable=True, assembly=False,
                    notes=L["notes"] + f"\n\nOrdered 2026-10-18 to The Villages FL (LRD), "
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

# ------------------------------------------------------------ PO
po = PurchaseOrder(
    supplier=amazon,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=f"Amazon order {ORDER} — Hollyland Lark M2 wireless mic kit (to The Villages FL)",
    issue_date=TODAY, target_date=datetime.date(2026, 10, 19),
    status=PurchaseOrderStatus.PLACED.value,
    notes=(f"Auto-created by the queue C daytime sweep, {RUN}.\n\n"
           "Ships to The Villages FL (LRD).\n\n"
           "PRICE SOURCE: the order-details page — $99.00 for the Hollyland Lark M2 kit. "
           "Item(s) Subtotal $99.00, shipping $0.00, tax $6.93, Grand Total $105.93.\n\n"
           "The $105.93 grand total includes tax; it is not a price and is deliberately not "
           "on the line.\n\nPLACED, not received."),
)
po.save()
po.refresh_from_db()
assert po.status == PurchaseOrderStatus.PLACED.value
assert po.supplier_reference == ORDER and po.reference != ORDER
li = PurchaseOrderLineItem(
    order=po, part=sp, quantity=1,
    purchase_price=L["price"], purchase_price_currency="USD",
    notes=f"Per-item price from the Amazon order-details page (${L['price']}, sold by "
          f"{L['seller']}), NOT the $105.93 grand total.")
li.save()
li.refresh_from_db()
assert float(li.purchase_price.amount) == float(L["price"]), li.purchase_price
print(f"  line: sp #{sp.pk} qty {li.quantity} @ {li.purchase_price}")
po.refresh_from_db()
print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
      f"target={po.target_date} lines={po.lines.count()}")
