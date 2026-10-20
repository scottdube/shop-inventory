"""Queue C, 22:40 daytime sweep 2026-10-19: two Amazon orders -> two POs, one line each.

  113-3442304-2237844  placed 2026-10-19, ship to The Villages FL (LRD), "Arriving tomorrow" (10-20)
    1. Hollyland Lark M2 Wireless Microphone, USB-C mini lapel (mobile variant)
                                        B0CP7P4RRQ  sold by Hollyland Official Store  $68.40 x1
       (re-buy after the 2TX+3RX kit on PO-0265 / 113-2965388-1706666 went back for return 10-19)

  113-7129720-7732203  placed 2026-10-19, ship to The Villages FL (LRD), "Arriving tomorrow" (10-20)
    1. ULANZI ST-14 smartphone tripod mount adapter, aluminum, cold shoe
                                        B08H1NGLLF  sold by SHUHEStore  $35.99 x1

AMAZON PRICE SOURCE -- the order-details pages, read in Chrome 2026-10-19 22:4x:
  113-3442304-2237844: Item(s) Subtotal $68.40, shipping $0.00, tax $4.79, Grand Total $73.19.
  113-7129720-7732203: Item(s) Subtotal $35.99, shipping $0.00, tax $2.52, rewards points
                       -$14.11, Grand Total $24.40.  The $24.40 is NOT a price: $14.11 of
                       Amazon Visa rewards were applied invisibly -- exactly the trap the task
                       file names.  The line carries $35.99.

PACK: each is one unit -> pack_quantity 1.

Dry run lists existing candidate parts and categories. Pass --mic-cat / --tripod-cat <pk>
(or --mic-part / --tripod-part <pk> to reuse) and --commit to write. PLACED, never received.
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

RUN = "22:40 daytime sweep 2026-10-19"
TODAY = datetime.date(2026, 10, 19)
ARRIVE = datetime.date(2026, 10, 20)

ORDERS = {
    "mic": dict(
        order="113-3442304-2237844",
        asin="B0CP7P4RRQ", price="68.40", pack="1", seller="Hollyland Official Store",
        subtotal="68.40", tax="4.79", total="73.19", adj="",
        name="Microphone kit, wireless, Hollyland Lark M2, USB-C mobile variant",
        desc=("orig: Hollyland Lark M2 Wireless Microphone for iPhone15/16/17&Android, USB C Mini "
              "Lapel Microphone Wireless, 1000ft Range, Hi-Fi Audio, Noise Cancellation, 30H "
              "Battery for Video Recording, Streaming; Amazon B0CP7P4RRQ"),
        kw=("microphone, mic, wireless, wireless mic, lavalier, lav, lapel, Lark M2, Hollyland, "
            "transmitter, receiver, USB-C, phone, iPhone, Android, video, recording, streaming"),
        sp_desc="Hollyland Lark M2 wireless mic, USB-C mobile variant",
        notes=("Hollyland Lark M2 wireless lapel microphone, the USB-C mobile variant (listing: "
               "iPhone 15/16/17 and Android, 1000 ft range, noise cancellation, 30 h battery). "
               "The listing does not state the transmitter/receiver count; read it off the box. "
               "Bought after the 2TX+3RX+case kit (PO-0265, order 113-2965388-1706666) was "
               "returned. One KIT -> pack_quantity 1."),
        po_desc="Amazon order 113-3442304-2237844 — Hollyland Lark M2 USB-C wireless mic (to The Villages FL)",
        hits=Q(name__icontains="hollyland") | Q(description__icontains="hollyland")
             | Q(description__icontains="B0CP7P4RRQ") | Q(name__icontains="lark")
             | Q(name__icontains="microphone"),
        cats=Q(name__icontains="audio") | Q(name__icontains="video") | Q(name__icontains="micro")
             | Q(name__icontains="media") | Q(name__icontains="camera"),
    ),
    "tripod": dict(
        order="113-7129720-7732203",
        asin="B08H1NGLLF", price="35.99", pack="1", seller="SHUHEStore",
        subtotal="35.99", tax="2.52", total="24.40", adj="rewards points -$14.11, ",
        name="Phone tripod mount, ULANZI ST-14, aluminum clamp with cold shoe",
        desc=("orig: Cell Phone Tripod Mount, ULANZI ST-14 Smartphone Tripod Mount Adapter | "
              "Aluminum with Cold Shoe, 360° Cell Phone Stand Holder Clamp for iPhone17 16 15 14 "
              "13 12 11 Max Pro iPhone X XR Xs 6 7 Plus; Amazon B08H1NGLLF"),
        kw=("tripod mount, phone mount, phone clamp, smartphone, ULANZI, ST-14, cold shoe, "
            "1/4-20, aluminum, camera, video, recording, iPhone, holder, adapter"),
        sp_desc="ULANZI ST-14 aluminum phone tripod mount with cold shoe",
        notes=("ULANZI ST-14 smartphone tripod mount adapter: aluminum clamp, 360-degree, cold "
               "shoe on top, 1/4-20 tripod thread. Video-recording rig for the phone. One unit "
               "-> pack_quantity 1."),
        po_desc="Amazon order 113-7129720-7732203 — ULANZI ST-14 phone tripod mount (to The Villages FL)",
        hits=Q(name__icontains="ulanzi") | Q(description__icontains="ulanzi")
             | Q(description__icontains="B08H1NGLLF") | Q(name__icontains="tripod")
             | Q(name__icontains="phone mount") | Q(name__icontains="cold shoe"),
        cats=Q(name__icontains="video") | Q(name__icontains="camera") | Q(name__icontains="photo")
             | Q(name__icontains="media") | Q(name__icontains="mount") | Q(name__icontains="audio"),
    ),
}

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--mic-cat", type=int)
ap.add_argument("--mic-part", type=int)
ap.add_argument("--tripod-cat", type=int)
ap.add_argument("--tripod-part", type=int)
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

# ------------------------------------------------------------ checks
for key, L in ORDERS.items():
    dup = PurchaseOrder.objects.filter(Q(supplier_reference=L["order"]) | Q(reference=L["order"]))
    if dup.exists():
        sys.exit(f"!! PO already exists for {L['order']}: {[p.reference for p in dup]}")
    assert len(L["kw"]) <= 250 and len(L["name"]) <= 100 and len(L["desc"]) <= 250, \
        (key, len(L["kw"]), len(L["name"]), len(L["desc"]))
    print(f"--- {key}: {L['name']}")
    sp = SupplierPart.objects.filter(SKU__iexact=L["asin"]).first()
    if sp:
        print(f"  supplier part {L['asin']} already exists: sp #{sp.pk} -> part #{sp.part_id}")
    for h in Part.objects.filter(L["hits"])[:40]:
        print(f"  candidate part #{h.pk}: {h.name}  active={h.active}  cat={h.category_id}: {h.category}")
    print("  categories:")
    for c in PartCategory.objects.filter(L["cats"]):
        print(f"    {c.pk}: {c.pathstring}  ({c.parts.count()} parts)")

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --mic-cat/--tripod-cat <pk> (or --*-part <pk>) --commit")


def build(key, L, cat_pk, part_pk):
    sp = SupplierPart.objects.filter(SKU__iexact=L["asin"]).first()
    if sp:
        print(f"REUSING sp #{sp.pk} part #{sp.part_id}")
    else:
        if part_pk:
            part = Part.objects.get(pk=part_pk)
            print(f"REUSING part #{part.pk} {part.name}")
        else:
            assert cat_pk, f"need --{key}-cat or --{key}-part"
            cat = PartCategory.objects.get(pk=cat_pk)
            part = Part(name=L["name"], description=L["desc"], category=cat, keywords=L["kw"],
                        component=False, purchaseable=True, assembly=False,
                        notes=L["notes"] + f"\n\nOrdered 2026-10-19 to The Villages FL (LRD), "
                              f"Amazon {L['order']}.\n\nCreated by the queue C daytime sweep, {RUN}.")
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

    po = PurchaseOrder(
        supplier=amazon,
        reference=PurchaseOrder.generate_reference(),
        supplier_reference=L["order"],
        description=L["po_desc"],
        issue_date=TODAY, target_date=ARRIVE,
        status=PurchaseOrderStatus.PLACED.value,
        notes=(f"Auto-created by the queue C daytime sweep, {RUN}.\n\n"
               "Ships to The Villages FL (LRD).\n\n"
               f"PRICE SOURCE: the order-details page — ${L['price']} for the item. "
               f"Item(s) Subtotal ${L['subtotal']}, shipping $0.00, tax ${L['tax']}, "
               f"{L['adj']}Grand Total ${L['total']}.\n\n"
               f"The ${L['total']} grand total is not a price and is deliberately not on the "
               "line.\n\nPLACED, not received."),
    )
    po.save()
    po.refresh_from_db()
    assert po.status == PurchaseOrderStatus.PLACED.value
    assert po.supplier_reference == L["order"] and po.reference != L["order"]
    li = PurchaseOrderLineItem(
        order=po, part=sp, quantity=1,
        purchase_price=L["price"], purchase_price_currency="USD",
        notes=f"Per-item price from the Amazon order-details page (${L['price']}, sold by "
              f"{L['seller']}), NOT the ${L['total']} grand total.")
    li.save()
    li.refresh_from_db()
    assert float(li.purchase_price.amount) == float(L["price"]), li.purchase_price
    print(f"  line: sp #{sp.pk} qty {li.quantity} @ {li.purchase_price}")
    po.refresh_from_db()
    print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
          f"target={po.target_date} lines={po.lines.count()}")


build("mic", ORDERS["mic"], args.mic_cat, args.mic_part)
build("tripod", ORDERS["tripod"], args.tripod_cat, args.tripod_part)
