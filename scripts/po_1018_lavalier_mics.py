"""Queue C, 12:40 daytime sweep 2026-10-18: one Amazon order -> one PO, two lines.

  113-7875038-0724220  placed 2026-10-18, ship to The Villages FL (LRD), "Arriving tomorrow" (10-19)
    1. Wireless Lavalier Microphone for iPhone & Android, 2 Pack Mini Mic with
       USB-C/Lightning/USB-A Receiver   B0FHRGL3F2  sold by PowerDeWise  $24.91 x1
    2. PowerDeWise Professional Grade Lavalier Clip On Microphone, 3.5mm
                                        B01AG56HYQ  sold by PowerDeWise  $24.91 x1

AMAZON PRICE SOURCE -- the order-details page: Item(s) Subtotal $49.82 (= 24.91 + 24.91, so
qty 1 each; no quantity badge on either line), shipping $0.00, tax $3.48, Grand Total $53.30.
The grand total is not a price.

PACKS: the wireless kit is ONE system (two transmitters sharing one receiver with its plug
adapters) -- an assortment, not a multipack of interchangeable pieces -> pack_quantity 1.
The wired lav is one microphone -> pack_quantity 1.

Dry run lists existing candidate parts and categories. Pass --part-a / --part-b <pk> to
reuse an existing part, --cat-a / --cat-b <pk> to create. --commit writes. PLACED, never
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

RUN = "12:40 daytime sweep 2026-10-18"
TODAY = datetime.date(2026, 10, 18)
ORDER = "113-7875038-0724220"

LINES = {
    "a": dict(
        asin="B0FHRGL3F2", price="24.91", pack="1", seller="PowerDeWise",
        name="Microphone kit, wireless lavalier, 2 TX + USB-C/Lightning/USB-A RX, PowerDeWise",
        desc=("orig: Wireless Lavalier Microphone for iPhone & Android, 2 Pack Mini Mic with "
              "USB-C/Lightning/USB-A Receiver, Plug & Play No Bluetooth, AI Noise Cancelling "
              "Lapel Mic for TikTok YouTube Vlog Podcast; Amazon B0FHRGL3F2"),
        kw=("microphone, mic, lavalier, lav, lapel, wireless, wireless mic, USB-C, Lightning, "
            "USB-A, receiver, video, recording, podcast, PowerDeWise"),
        sp_desc="PowerDeWise wireless lavalier mic kit, 2 transmitters + 1 receiver",
        notes=("Wireless lavalier microphone system: two clip-on transmitters sharing one "
               "receiver with USB-C, Lightning and USB-A plugs; listing says no Bluetooth, "
               "plug and play. One KIT (not a multipack of interchangeable pieces) -> "
               "pack_quantity 1."),
        hits=Q(name__icontains="powerdewise") | Q(description__icontains="powerdewise")
             | Q(description__icontains="B0FHRGL3F2") | Q(name__icontains="lavalier")
             | Q(name__icontains="microphone") | Q(name__icontains="mic,"),
    ),
    "b": dict(
        asin="B01AG56HYQ", price="24.91", pack="1", seller="PowerDeWise",
        name="Microphone, wired lavalier clip-on, 3.5 mm, PowerDeWise",
        desc=("orig: PowerDeWise Professional Grade Lavalier Clip On Microphone - Lav Mic for "
              "Camera Phone iPhone GoPro Video Recording ASMR - Small Noise Cancelling 3.5mm "
              "Tiny Shirt Microphone with Easy Clip On System; Amazon B01AG56HYQ"),
        kw=("microphone, mic, lavalier, lav, lapel, clip-on, wired, 3.5mm, TRRS, video, "
            "recording, camera, GoPro, PowerDeWise"),
        sp_desc="PowerDeWise wired clip-on lavalier mic, 3.5 mm",
        notes=("Wired clip-on lavalier microphone on a 3.5 mm plug. One microphone -> "
               "pack_quantity 1."),
        hits=Q(name__icontains="powerdewise") | Q(description__icontains="B01AG56HYQ")
             | Q(name__icontains="lav"),
    ),
}

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--cat-a", type=int)
ap.add_argument("--cat-b", type=int)
ap.add_argument("--part-a", type=int)
ap.add_argument("--part-b", type=int)
args = ap.parse_args()
choice = {"a": (args.cat_a, args.part_a), "b": (args.cat_b, args.part_b)}

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
for c in PartCategory.objects.filter(Q(name__icontains="audio") | Q(name__icontains="video")
                                     | Q(name__icontains="camera") | Q(name__icontains="micro")
                                     | Q(name__icontains="media") | Q(name__icontains="photo")
                                     | Q(name__icontains="electronics") | Q(name__icontains="equipment")):
    print(f"  {c.pk}: {c.pathstring}  ({c.parts.count()} parts)")

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --cat-a/--cat-b <pk> (or --part-a/--part-b <pk>) --commit")

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
    sps[k] = sp

# ------------------------------------------------------------ PO
po = PurchaseOrder(
    supplier=amazon,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=f"Amazon order {ORDER} — PowerDeWise wireless lav kit + wired lav mic (to The Villages FL)",
    issue_date=TODAY, target_date=datetime.date(2026, 10, 19),
    status=PurchaseOrderStatus.PLACED.value,
    notes=(f"Auto-created by the queue C daytime sweep, {RUN}.\n\n"
           "Ships to The Villages FL (LRD).\n\n"
           "PRICE SOURCE: the order-details page — $24.91 for the PowerDeWise wireless "
           "lavalier kit, $24.91 for the PowerDeWise wired 3.5 mm lavalier. Item(s) Subtotal "
           "$49.82, shipping $0.00, tax $3.48, Grand Total $53.30.\n\n"
           "The $53.30 grand total includes tax; it is not a price and is deliberately not "
           "on any line.\n\nPLACED, not received."),
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
              f"{L['seller']}), NOT the $53.30 grand total.")
    li.save()
    li.refresh_from_db()
    assert float(li.purchase_price.amount) == float(L["price"]), li.purchase_price
    print(f"  line {k}: sp #{sps[k].pk} qty {li.quantity} @ {li.purchase_price}")
po.refresh_from_db()
print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
      f"target={po.target_date} lines={po.lines.count()}")
