"""Queue C for the 2026-09-09 22:40 daytime sweep — one Amazon PO, a DP MST hub.

Window swept: last-po-sweep 2026-09-09 minus 1 day = from 2026-09-08.

WHAT WAS IN THE WINDOW. Four vendor order references, checked as one batch
through po_check.py, which is the idempotency gate:

  113-2048573-8975434  absent   <- imported here (Monoprice DP->HDMI MST hub)
  113-7332958-8875426  PO-0162  (Placed — created by THIS afternoon's 16:40 run)
  8214467898875753     PO-0148  (Complete)
  8214467898895753     PO-0149  (Complete)

The two AliExpress numbers are in the window only because AliExpress sent
"how did it go?" nags for orders imported days ago. Not new work.

THE ORDER HISTORY PAGE FOUND THIS ONE TOO, and that is the second consecutive
sweep where it did. The confirmation mail is subject "Ordered: 1 Electronics
item" from auto-confirm@amazon.com, carrying no order number in the subject
line at all. The 16:40 run wrote up the same failure mode for its own order.
Two for two: the Amazon order-history page is ground truth, the mail search is
convenience, and a quiet mail search is not evidence that nothing was bought.

PRICE: $18.46, qty 1, read from the order-details page, the only sanctioned
Amazon source. Item line $18.46, Item(s) Subtotal $18.46, Shipping & Handling
$0.00, Estimated tax $0.00, Grand Total $18.46. Nothing masked on this order —
no rewards points, no gift card. The LINE was still the source; whether the
total happens to agree is not observable from the email, which is the whole
reason the rule says read the page.

SOLD BY AMAZON RESALE, CONDITION "Used - Mint". This is recorded on the PO and
in the part notes because it changes what lands on the shelf: the piece that
arrives is open-box/returned stock, not new, and if it turns out to be dead on
arrival the return window (through the order page) is the recourse, not a
warranty claim against Monoprice. It also means the $18.46 is NOT the price of
a new one — do not read this line as a reorder price.

CATEGORY flat `Modules` (pk 22, 49 active parts), following #477 BENFEI HDMI to
VGA — an Amazon-bought, consumer-packaged, active video-signal converter, which
is exactly what this is, and the same place the micro-HDMI adapters #255/#272
live. NOT `Electronics/Modules/Video` (pk 124): it holds exactly one part,
#726, a bare TC358743 bridge BOARD. That is the shadow-root split this instance
already knows about, and the standing observation is that the flat side wins;
putting a second dongle behind a three-deep path would deepen the split for one
item. Measured both sides before choosing rather than following the one
prettier precedent.

default_location left EMPTY on purpose — nobody has told this job where video
adapters go home, and default_location means where a SPARE lives. The receive
step takes an explicit --to.

Searched before creating across name/description/IPN/keywords and SupplierPart
SKU (monoprice, displayport, "display port", MST, multi-stream, HDMI,
B07575NBTV, hub, 4K, "DP 1.2", "video adapter", splitter): 40 distinct parts
matched on the loose terms, and ZERO on any DisplayPort term — no part on this
instance mentions DisplayPort at all, and no SupplierPart carries this ASIN.
Nearest neighbours are #477 (HDMI->VGA), #726 (HDMI->CSI-2) and #1145 (a
micro-HDMI pigtail), none of which is a DisplayPort source. New part.

PO left in PLACED. Nothing received, no stock created.
"""
import os
import sys
from datetime import date
from decimal import Decimal

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402
from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402
from InvenTree.helpers_model import get_base_url  # noqa: E402

AMAZON = Company.objects.get(pk=9)
ISSUE = date(2026, 9, 9)
ARRIVES = date(2026, 9, 14)          # order page: "Arriving Monday"

ORDERS = [
    dict(
        ref="113-2048573-8975434",
        asin="B07575NBTV",
        price="18.46",
        qty="1",
        pack="1",
        category="Modules",
        name="DisplayPort 1.2 to 2x HDMI MST Hub, 4K@30Hz, Monoprice",
        description=("orig: Monoprice 2-Port DisplayPort 1.2 to HDMI "
                     "Multi-Stream Transport (MST) Hub, 4K@30Hz for 2 "
                     "Displays, 21.6 Gbps Bandwidth, 11.8 Inch Cable, Black"),
        # Part.keywords is capped at 250 characters and Part.save() calls
        # full_clean(), so an over-long list is a hard ValidationError.
        keywords=("DisplayPort, DP, DisplayPort 1.2, MST, multi-stream "
                  "transport, HDMI, video hub, dual monitor, two displays, "
                  "dual head, extended desktop, 4K, 4K30, 21.6Gbps, splitter, "
                  "adapter, dongle, Monoprice, B07575NBTV, video adapter"),
        sold_by="Amazon Resale",
        condition="Used - Mint",
        price_note=(
            "$18.46, qty 1, read from the order-details page — item line "
            "$18.46, Item(s) Subtotal $18.46, Shipping & Handling $0.00, "
            "Estimated tax $0.00, Grand Total $18.46.\n\n"
            "Nothing is masked on this order: no rewards points, no gift "
            "card. The line was still the source. The rule is not 'use the "
            "total when it matches' — whether it matches is not visible from "
            "the email, which is exactly why the rule says read the page.\n\n"
            "THIS IS NOT A REORDER PRICE. The unit was sold by Amazon Resale "
            "in 'Used - Mint' condition. A new one costs more; do not read "
            "$18.46 off this line as the cost to buy another."
        ),
        notes=(
            "AN MST HUB IS NOT AN HDMI SPLITTER, and the difference is what "
            "makes this part either useful or useless in a given spot. A "
            "splitter shows the SAME picture on two screens. This drives TWO "
            "INDEPENDENT displays off one DisplayPort output, and it does it "
            "by asking the SOURCE to render both — so the source GPU and its "
            "driver must support DisplayPort 1.2 Multi-Stream Transport. Plug "
            "it into a DP 1.1 output, or an HDMI output through a passive "
            "adapter, and you get one display or none. Check the source "
            "before blaming the hub.\n\n"
            "4K IS 30 Hz HERE, and only on one display. 21.6 Gbps of DP 1.2 "
            "bandwidth is being divided between two streams; the usual "
            "workable pairing is 2x 1920x1080 or 2x 2560x1440 at 60 Hz. "
            "Treat 4K@30 as the headline number, not the two-display "
            "number.\n\n"
            "CONDITION: Used - Mint, sold by Amazon Resale on order "
            "113-2048573-8975434. Open-box/returned stock, not new. If it is "
            "dead on arrival the recourse is the Amazon return window on that "
            "order, not a Monoprice warranty. Worth testing on arrival rather "
            "than shelving it untested — a used active adapter that fails "
            "quietly six months from now will look like a cabling fault.\n\n"
            "The 11.8 inch figure in the vendor title is the CAPTIVE DP "
            "PIGTAIL on the hub body, not a separate cable in the box. The "
            "two HDMI ports are sockets — HDMI cables are not included and "
            "are not part of this line.\n\n"
            "pack_quantity is 1 and the line quantity is 1: one hub.\n\n"
            "default_location deliberately EMPTY — nobody has said where "
            "video adapters live, and default_location means where a SPARE "
            "goes home. Receiving takes an explicit --to.\n\n"
            "CATEGORY flat Modules (pk 22, 49 active), following #477 BENFEI "
            "HDMI to VGA — an Amazon-bought consumer-packaged active video "
            "converter, the same kind of object, alongside the micro-HDMI "
            "adapters #255 and #272. NOT Electronics/Modules/Video (pk 124), "
            "which holds one part, #726, a bare TC358743 bridge BOARD. Both "
            "sides were counted before choosing; this is the known shadow-root "
            "split and the flat side is the populated one.\n\n"
            "Searched before creating across name/description/IPN/keywords "
            "and SupplierPart SKU (monoprice, displayport, display port, MST, "
            "multi-stream, HDMI, B07575NBTV, hub, 4K, DP 1.2, video adapter, "
            "splitter): 40 parts matched the loose terms and ZERO matched any "
            "DisplayPort term — no part on this instance mentions DisplayPort "
            "at all. Nearest are #477 HDMI->VGA, #726 HDMI->CSI-2 and #1145 a "
            "micro-HDMI pigtail, none of them a DisplayPort source. New part."
        ),
    ),
]

base = get_base_url() or "http://192.168.50.10:8001"
created = []

for o in ORDERS:
    ref, asin = o["ref"], o["asin"]
    print("=" * 72)

    if PurchaseOrder.objects.filter(supplier_reference=ref).exists():
        print(f"ALREADY EXISTS {ref} — skipping (idempotency key is supplier_reference)")
        continue

    sp = SupplierPart.objects.filter(supplier=AMAZON, SKU=asin).first()
    if sp:
        print(f"reuse  SupplierPart {sp.pk}  {asin} -> part {sp.part_id} {sp.part.name}")
    else:
        for field, value in (("name", o["name"]), ("IPN", asin)):
            dupe = Part.objects.filter(**{field: value}).first()
            if dupe:
                raise SystemExit(
                    f"refusing to create: part with {field}={value!r} exists (#{dupe.pk})")

        category = PartCategory.objects.get(pathstring=o["category"])

        p = Part.objects.create(
            name=o["name"],
            description=o["description"],
            keywords=o["keywords"],
            IPN=asin,
            category=category,
            default_location=None,
            component=True,
            purchaseable=True,
            active=True,
        )
        check = Part.objects.get(pk=p.pk)      # silent-save trap: re-read
        assert check.name == o["name"] and check.IPN == asin, f"part {p.pk} did not stick"
        assert check.keywords, f"part {p.pk} lost its keywords"
        print(f"CREATE part {check.pk}: {check.name[:60]}  cat={check.category.pathstring}")
        p = check

        # .create() goes through save() -> clean(), which is what populates
        # pack_quantity_native. A queryset .update() would set only the text field
        # and leave the number that receiving actually reads at 1.
        sp = SupplierPart.objects.create(
            supplier=AMAZON, part=p, SKU=asin, pack_quantity=o["pack"],
        )
        fresh = SupplierPart.objects.get(pk=sp.pk)
        assert fresh.SKU == asin, f"supplierpart {sp.pk} did not stick"
        assert fresh.part_id == p.pk, f"supplierpart {sp.pk} attached to the wrong part"
        assert str(fresh.pack_quantity) == o["pack"], (
            f"supplierpart {sp.pk} pack_quantity={fresh.pack_quantity!r}, want {o['pack']!r}")
        assert Decimal(fresh.pack_quantity_native) == Decimal(o["pack"]), (
            f"supplierpart {sp.pk} pack_quantity_native={fresh.pack_quantity_native!r} "
            f"does not match pack_quantity={fresh.pack_quantity!r} — the split-field trap")
        print(f"CREATE SupplierPart {fresh.pk}: {asin} -> part {fresh.part_id} "
              f"pack_quantity={fresh.pack_quantity} native={fresh.pack_quantity_native}")
        sp = fresh

    notes = (
        f"Amazon order {ref}, placed {ISSUE:%Y-%m-%d}, arriving {ARRIVES:%A %Y-%m-%d}.\n"
        f"Sold by: {o['sold_by']}.  Condition: {o['condition']}.\n\n"
        f"{o['price_note']}\n\n"
        f"{o['notes']}"
    )

    po = PurchaseOrder.objects.create(
        reference=PurchaseOrder.generate_reference(),
        supplier=AMAZON,
        supplier_reference=ref,
        description=f"Amazon order {ref}",
        notes=notes,
        issue_date=ISSUE,
        target_date=ARRIVES,
    )
    po.status = PurchaseOrderStatus.PLACED.value
    po.save()

    po = PurchaseOrder.objects.get(pk=po.pk)
    assert po.supplier_reference == ref, "PO supplier_reference did not stick"
    assert po.issue_date == ISSUE, "PO issue_date did not stick"
    assert po.target_date == ARRIVES, "PO target_date did not stick"
    assert po.status == PurchaseOrderStatus.PLACED.value, f"PO status is {po.status}, not PLACED"
    print(f"CREATE {po.reference}  status=PLACED  supplier_reference={po.supplier_reference}")

    li = PurchaseOrderLineItem.objects.create(
        order=po, part=sp, quantity=Decimal(o["qty"]), purchase_price=Decimal(o["price"]),
    )
    li = PurchaseOrderLineItem.objects.get(pk=li.pk)
    assert li.purchase_price.amount == Decimal(o["price"]), f"line {li.pk} price did not stick"
    assert li.quantity == Decimal(o["qty"]), f"line {li.pk} quantity did not stick"
    print(f"LINE {li.pk}: {sp.part.name[:55]} qty={li.quantity} unit={li.purchase_price} "
          f"pack={sp.pack_quantity_native}")

    created.append((po.reference, ref, po.pk))

print("=" * 72)
for reference, ref, pk in created:
    print(f"{reference}  {ref}  {base}/order/purchase-order/{pk}/")
print(f"{len(created)} PO(s) created, all left in PLACED — nothing received, no stock made.")
