"""Queue C for the 2026-09-10 22:40 daytime sweep — one Amazon PO.

Window swept: last-po-sweep 2026-09-10 minus 1 day = from 2026-09-09.

WHAT WAS IN THE WINDOW. Eight vendor order references, all checked through
po_check.py in two batches — po_check is the idempotency gate and it takes any
number of arguments, so this is two calls, not a loop:

  113-8888047-4781028  absent   <- imported here (VSDISPLAY 12.6in bar monitor)
  113-9155135-6305031  PO-0165  (Placed, imported by the 16:40 run)
  113-2932029-5857069  PO-0166  (Placed, imported by the 16:40 run)
  113-6595171-3994627  PO-0167  (Placed, imported by the 16:40 run)
  113-2048573-8975434  PO-0163  (Placed, imported 09-10 12:40)
  113-7332958-8875426  PO-0162  (Placed, imported 09-09 16:40)
  8214467898875753     PO-0148  (Complete)
  8214467898895753     PO-0149  (Complete)

The two AliExpress numbers are in the Gmail window only because AliExpress sent
"Order N: how did it go?" review nags for orders imported days ago. A review
nag is not an order confirmation; checking them cost one po_check argument and
is cheaper than reasoning about it.

THE ORDER HISTORY PAGE FOUND THIS ORDER; GMAIL WOULD NOT HAVE, BY TIMING.
The confirmation for 113-8888047-4781028 landed at 2026-09-11T01:41Z — 21:41
EDT, one hour before this run — as a FOURTH message inside Gmail thread
1a08c9515ca6f238, under the same subject "Ordered: 1 Electronics item" as the
three orders the 16:40 run already imported. A sweep that read threads rather
than messages would have seen that thread as handled and stopped. This is the
fourth consecutive run (09-02, 09-09, 09-10 16:40, 09-10 22:40) in which the
order history page was the thing that actually produced the census, by four
different failure modes. It is the census; Gmail is the supplement.

PRICE — READ FROM THE ORDER-DETAILS PAGE, and it is the clean case:

    Item(s) Subtotal        $156.00
    Shipping & Handling       $0.00
    Total before tax        $156.00
    Estimated tax             $0.00
    Grand Total             $156.00
    item line               $156.00

Nothing masked — no rewards points, no coupon, no gift card. The LINE was
still the source. Whether the line and the total agree is not observable from
the confirmation email, which is exactly why the rule reads the order page;
two of the three orders in this same day's 16:40 run had a hidden adjustment
(a $2.54 points line and a $7.35 coupon) and this one does not.

CATEGORY Displays (#25), with #1047 (WIMAXIT M1560CTV2 15.6in portable
monitor) — the only other complete, self-contained monitor on the instance —
and with #397, the previous VSDISPLAY panel. NOT Modules/Display, which holds
bare panels and driver boards (#1073 bare round LCD, #1074 its driver board,
#99 the DVI/VGA controller): those are things you build INTO something. This
is a finished monitor you plug into a PC.

#397 IS NOT A DUPLICATE AND NOT A LIVE EQUIVALENT. It is VSDISPLAY too, and
it is active=False with 0 stock, which on this instance usually means a merge
receipt — so it was read rather than assumed. Its description says "RETURNED
to vendor, credit received (Amazon 113-3985914-5950615), confirmed by Scott
2026-08-25". It is a return tombstone, a different product (10.4in 1024x768
with a controller board), and nothing merged into it.

SEARCHED BEFORE CREATING (dupe_probe_0910_2240.py) across name / description /
IPN / keywords and supplier SKU + description + note + manufacturer MPN, on 22
terms covering the ASIN, VSDISPLAY, the resolution, and the monitor / display
/ panel / LCD / IPS / driver-board clusters. Zero hits on B0C3CSW624. The 49
existing display-ish parts were listed in full, not truncated. New part.

default_location left EMPTY on purpose — nobody has said where a spare monitor
lives, and default_location means where a SPARE goes home. Receiving takes an
explicit --to.

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
ISSUE = date(2026, 9, 10)

ORDERS = [
    dict(
        ref="113-8888047-4781028",
        asin="B0C3CSW624",
        price="156.00",
        qty="1",
        pack="1",
        arrives=date(2026, 9, 12),
        category="Displays",
        name="VSDISPLAY 12.6in Bar Monitor, 1920x515 IPS",
        description=("orig: VSDISPLAY 12.6'' IPS LCD Screen Monitor 1920x515 "
                     "as PC Second Display"),
        # Part.keywords is capped at 250 characters and Part.save() calls
        # full_clean(), so an over-long list is a hard ValidationError.
        keywords=("bar monitor, stretched display, strip display, 1920x515, "
                  "12.6 inch, IPS, LCD, second display, secondary monitor, "
                  "wide aspect, instrument panel, dashboard, sim panel, "
                  "VSDISPLAY, PC monitor"),
        sold_by="Shenzhen Shi Wei Si Dian Zi You Xian Gong Si",
        price_note=(
            "$156.00, qty 1, read from the order-details page — item line "
            "$156.00, Item(s) Subtotal $156.00, Shipping & Handling $0.00, "
            "Total before tax $156.00, Estimated tax $0.00, Grand Total "
            "$156.00.\n\n"
            "Nothing is masked on this order: no rewards points, no coupon, "
            "no gift card. Line and total agree. The LINE was still the "
            "source — whether they agree is not observable from the "
            "confirmation email, which is the whole reason the rule reads the "
            "order page. Two of the three orders imported earlier the same "
            "day each hid an adjustment behind an agreeable-looking total."
        ),
        notes=(
            "A 12.6in STRETCHED BAR PANEL, 1920x515. The aspect ratio is "
            "about 3.7:1 — this is not a small conventional monitor, it is a "
            "wide strip, the shape used for instrument strips, status bars "
            "and sim panels. Recorded because the size alone ('12.6 inch') "
            "reads as an ordinary tablet-sized screen and would be mentally "
            "filed as one.\n\n"
            "THE INPUT CONNECTOR IS NOT RECORDED, ON PURPOSE. The vendor "
            "title says only 'as PC Second Display' and states no interface; "
            "the order history and order-details pages were the only sources "
            "read for this order, and neither names one. VSDISPLAY panels "
            "ship with a variety of controller boards (#397, the returned "
            "10.4in, carried an HDMI/audio controller), so do NOT assume this "
            "one is HDMI. Read it off the unit when it lands and write it on "
            "this part.\n\n"
            "NOR IS A REFRESH RATE, BRIGHTNESS, OR TOUCH CAPABILITY CLAIMED. "
            "The title states none of them. #1047, the WIMAXIT, is a "
            "TOUCHSCREEN and that is its most useful property — do not carry "
            "that across to this part. Nothing here says this panel has "
            "touch.\n\n"
            "BOUGHT ALONGSIDE TWO MST HUBS. #1181 (DisplayPort 1.2 to 2x "
            "HDMI, order 113-2048573-8975434, 09-09) and #1185 (DisplayPort "
            "1.2 to 2x DisplayPort, order 113-9155135-6305031, 09-10) were "
            "ordered in the same 48 hours as this panel, along with "
            "right-angle USB-C adapters. That is noted as a PURCHASING "
            "coincidence worth knowing when this box is opened, not as a "
            "known plan — nobody has told this job what is being built, and "
            "an MST hub feeding this panel is a guess. If the three belong to "
            "one build, they want a project; ask Scott rather than inferring "
            "one.\n\n"
            "IF IT IS DRIVEN FROM AN MST HUB, CHECK THE MODE AT THE BENCH. An "
            "MST hub needs DisplayPort 1.2 MST enabled on the source GPU and "
            "some hosts drive one in MIRROR rather than extending the "
            "desktop. Same caution already written on #1185. A caution to "
            "verify, not a measured fact about this panel or any machine "
            "here.\n\n"
            "NOT A BARE PANEL. Filed in Displays with #1047, the only other "
            "complete self-contained monitor on the instance, rather than "
            "Modules/Display, which holds bare glass and driver boards "
            "(#1073, #1074, #99) — things built INTO something. If this turns "
            "out to arrive as a panel plus a loose controller board, that "
            "changes the category and the filing should be revisited.\n\n"
            "#397 IS THE SAME BRAND AND IS NOT RELATED STOCK. VSDISPLAY "
            "10.4in 1024x768, active=False, 0 stock — RETURNED to vendor with "
            "credit received on Amazon order 113-3985914-5950615, confirmed "
            "by Scott 2026-08-25. A return tombstone, not a merge receipt and "
            "not a spare.\n\n"
            "default_location deliberately EMPTY — nobody has said where a "
            "spare monitor lives, and default_location means where a SPARE "
            "goes home. Receiving takes an explicit --to. #1047 sits in "
            "SLN/Triage for exactly this reason.\n\n"
            "Searched before creating across name/description/IPN/keywords/"
            "SKU on 22 terms (B0C3CSW624, VSDISPLAY, 1920x515, bar monitor, "
            "stretched, ultrawide, second display, IPS, LCD monitor, display "
            "panel, eDP, LVDS, driver board, backlight): zero hits on the "
            "ASIN; the VSDISPLAY hit is #397 above. New part."
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
        assert check.category.pathstring == o["category"], (
            f"part {p.pk} landed in {check.category.pathstring}, want {o['category']}")
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

    arrives = o["arrives"]
    notes = (
        f"Amazon order {ref}, placed {ISSUE:%Y-%m-%d}, arriving {arrives:%A %Y-%m-%d}.\n"
        f"Sold by: {o['sold_by']}.\n\n"
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
        target_date=arrives,
    )
    po.status = PurchaseOrderStatus.PLACED.value
    po.save()

    po = PurchaseOrder.objects.get(pk=po.pk)
    assert po.supplier_reference == ref, "PO supplier_reference did not stick"
    assert po.issue_date == ISSUE, "PO issue_date did not stick"
    assert po.target_date == arrives, "PO target_date did not stick"
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
