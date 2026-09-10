"""Queue C for the 2026-09-10 16:40 daytime sweep — three Amazon POs.

Window swept: last-po-sweep 2026-09-10 minus 1 day = from 2026-09-09.

WHAT WAS IN THE WINDOW. Five vendor order references, checked as one batch
through po_check.py, which is the idempotency gate:

  113-9155135-6305031  absent   <- imported here (Monoprice DP->DP MST hub)
  113-2932029-5857069  absent   <- imported here (USB-C right-angle adapters)
  113-6595171-3994627  absent   <- imported here (USB-A to micro-USB cables)
  113-2048573-8975434  PO-0163  (Placed, imported by the 12:40 run)
  113-7332958-8875426  PO-0162  (Placed, imported by the 09-09 16:40 run)

Plus two AliExpress numbers in the Gmail window, 8214467898875753 and
8214467898895753, which are PO-0148 and PO-0149 (both Complete). They are in
the window only because AliExpress sent "how did it go?" review nags for
orders imported days ago. Not new work.

THE GMAIL SEARCH FOUND NONE OF THE THREE AMAZON ORDERS, AND THE REASON IS NOT
THE DOCUMENTED SUBJECT TRAP — IT WAS THIS RUN'S OWN QUERY. The vendor sweep
was written as

    after:2026/09/09 {from:tormach.com from:mscdirect.com from:shars.com
    from:mouser.com from:pololu.com from:ebay.com from:haascnc.com
    from:mcmaster.com from:digikey.com from:seeed.cc from:walmart.com
    from:aliexpress.com}

and `from:amazon.com` is simply NOT IN THE BRACE GROUP. Eleven of the twelve
itemised vendors were searched and the twelfth — the one that accounts for
most of the orders this queue ever imports — was silently absent. Six threads
came back, all marketing plus the two AliExpress nags, and that empty result
looked exactly like a quiet window.

Run afterwards as a check, `from:amazon.com after:2026/09/09` returns all
three confirmations immediately, with no subject filter needed. So this is a
THIRD instance of the general shape in TRAPS.md — a filter that excludes the
target returns success — but a NEW mechanism: not Gmail's word matching, an
omission in a hand-written OR list. The previous two write-ups are about
`subject:` vetoing the window; a session that had internalised those would
still have made this mistake.

All three orders came off the ORDER HISTORY PAGE, which is now the mechanism
that has caught this on 09-02, 09-09 and 09-10 — three times, by three
different failure modes. Treat it as the census, not the backstop.

AMAZON THREADS SAME-SUBJECT ORDERS TOGETHER, exactly as the task file warns
for Walmart. All three of these confirmations sit in ONE Gmail thread
(1a08c9515ca6f238) under the identical subject "Ordered: 1 Electronics item".
A sweep that counted threads would have seen one order here, not three. Read
the order number out of each MESSAGE — the Walmart rule is not
Walmart-specific.

PRICES — ALL THREE READ FROM THE ORDER-DETAILS PAGE, and order
113-2932029-5857069 is the exact shape the task file warns about:

    Item(s) Subtotal   $6.99
    Rewards Points    -$2.54
    Grand Total        $4.45

The item line reads $6.99. An importer trusting the email's Grand Total would
have booked these adapters at $4.45 — 36% low — because the points line is
invisible in the confirmation mail. The task file's worked example is the same
mechanism ($4.28 email vs $6.99/$9.49 real lines), and it settles which number
is the price: the ITEM LINE, not the points-reduced total. Same ruling applied
to 113-9155135-6305031, where a $7.35 coupon sits between a $44.99 line and a
$37.64 total. Booked at $44.99.

PACK QUANTITIES — two of the three are multipacks, which is the failure Scott
named on 2026-09-01 ("we seem to have this problem every time we buy something
that comes in a multipack"). Both are caught here at creation rather than at
receive time:

  B0H3JNGX1D  "4 Pack"  -> pack_quantity 4, line quantity 1
  B07QB6KL85  "5-Pack"  -> pack_quantity 5, line quantity 1
  B075754ZYC  one hub   -> pack_quantity 1, line quantity 1

The names deliberately do NOT say "4 pack" or "5 pack": stock counts PIECES
and the pack is a supplier fact. Written through .save() (via .create()), never
a queryset .update(), because only pack_quantity_native is read at receive time
and .update() sets the text field alone.

CATEGORIES:

  DP MST hub  -> Modules, matching its immediate sibling #1181 (DisplayPort
                 1.2 to 2x HDMI MST Hub, Monoprice), imported yesterday by
                 PO-0163. Same manufacturer, same function, one output
                 connector apart. Sibling precedent beats the tidier-looking
                 Electronics/Modules/Video, which holds exactly one part.
  USB-C adapter -> Electronics/Connectors/Adapters (#127). A passive connector
                 adapter, not a module. Filed with #729, the NRF24L01 socket
                 adapter plate.
  micro-USB cable -> Electronics/Cables (#119), with #1145 (micro-HDMI to HDMI
                 adapter cable) and the multi-conductor reels.

SEARCHED BEFORE CREATING (dupe_probe_0910_1640.py) across name / description /
IPN / keywords / supplier SKU + description + note + manufacturer MPN, on 26
terms covering all three ASINs and the MST, USB-C, right-angle, micro-USB and
Amazon Basics clusters. Zero hits on any of the three ASINs. Nearest neighbour
is #1181, the DP->HDMI hub — a different product (HDMI outputs), which is
precisely why the new part is named "to 2x DisplayPort" in the same shape, so
the two do not read as one object on a shelf.

default_location left EMPTY on all three on purpose — nobody has told this job
where video adapters or USB cabling live, and default_location means where a
SPARE goes home. The receive step takes an explicit --to.

All three POs left in PLACED. Nothing received, no stock created.
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
        ref="113-9155135-6305031",
        asin="B075754ZYC",
        price="44.99",
        qty="1",
        pack="1",
        arrives=date(2026, 9, 12),
        category="Modules",
        name="DisplayPort 1.2 to 2x DisplayPort MST Hub, Monoprice",
        description=("orig: Monoprice DisplayPort 1.2 to DisplayPort "
                     "Multi-Stream Transport (MST) Hub - 2-Port, DP to DP, "
                     "Ideal for Digital Signage, Large Video Displays in "
                     "Schools, 7.6 x 5.8 x 1.3"),
        # Part.keywords is capped at 250 characters and Part.save() calls
        # full_clean(), so an over-long list is a hard ValidationError.
        keywords=("MST hub, multi stream transport, DisplayPort, DP, DP 1.2, "
                  "DP to DP, 2 port, dual monitor, display splitter, daisy "
                  "chain, video, Monoprice, digital signage, extended "
                  "desktop, GPU, workstation"),
        sold_by="Amazon.com",
        price_note=(
            "$44.99, qty 1, read from the order-details page — item line "
            "$44.99, Item(s) Subtotal $44.99, Shipping & Handling $0.00, "
            "Your Coupon Savings -$7.35, Total before tax $37.64, Estimated "
            "tax $0.00, Grand Total $37.64.\n\n"
            "BOOKED AT THE LINE, $44.99, not the $37.64 paid. A $7.35 coupon "
            "sits between them. Same ruling as the rewards-points case on "
            "113-2932029-5857069 in this same run and the task file's own "
            "worked example, where the real items were $6.99 and $9.49 behind "
            "a $4.28 total: the ITEM LINE is the price. Recorded here so the "
            "$7.35 gap is not later mistaken for a transcription error."
        ),
        notes=(
            "TWO DisplayPort OUTPUTS FROM ONE DisplayPort SOURCE. This is the "
            "DP-output sibling of #1181, the DisplayPort 1.2 to 2x HDMI MST "
            "hub bought one day earlier on order 113-2048573-8975434 "
            "(PO-0163). Same maker, same MST function, different output "
            "connector. They are NOT interchangeable and are deliberately "
            "named in the same shape so the difference is the part of the "
            "name that differs.\n\n"
            "NO RESOLUTION IS RECORDED, on purpose. The sibling #1181 carries "
            "4K@30Hz because its vendor title states it; this title does not "
            "state a resolution at all, and the only sanctioned sources read "
            "for this order were the order history and order-details pages. "
            "Do not copy #1181's 4K@30Hz across — a different output stage is "
            "exactly the thing that would change it. Measure it against the "
            "actual displays when it lands, or read it off the unit.\n\n"
            "BEFORE RELYING ON IT, CHECK THE SOURCE SUPPORTS MST. An MST hub "
            "is not a passive splitter: it needs DisplayPort 1.2 MST enabled "
            "on the source GPU, and some hosts drive MST hubs in MIRROR only "
            "rather than extending the desktop — Apple Silicon Macs are the "
            "usual case. This is a caution to verify at the bench, NOT a "
            "measured fact about this unit or about any machine here. If it "
            "mirrors when it should extend, the host is the suspect before "
            "the hub is.\n\n"
            "The 7.6 x 5.8 x 1.3 in the vendor title is PACKAGE dimensions, "
            "not the hub. No unit size recorded.\n\n"
            "default_location deliberately EMPTY — nobody has said where "
            "video adapters live, and default_location means where a SPARE "
            "goes home. Receiving takes an explicit --to.\n\n"
            "CATEGORY Modules, following #1181 directly. Not "
            "Electronics/Modules/Video, which holds one part (#726, an "
            "HDMI-to-CSI-2 bridge) and would separate these two siblings "
            "across the instance's two parallel category roots.\n\n"
            "Searched before creating across name/description/IPN/keywords/"
            "SKU on 26 terms (B075754ZYC, MST, Multi-Stream, DisplayPort, DP "
            "hub, Monoprice, display hub, video splitter, daisy chain, and "
            "the USB clusters): the only hits anywhere near were #1181. New "
            "part."
        ),
    ),
    dict(
        ref="113-2932029-5857069",
        asin="B0H3JNGX1D",
        price="6.99",
        qty="1",
        pack="4",
        arrives=date(2026, 9, 11),
        category="Electronics/Connectors/Adapters",
        name="USB-C Right-Angle Adapter, male to female, 90 deg, 100W",
        description=("orig: Vanjua 4 Pack 90 Degree USB-C Male to Female "
                     "Adapter, Right Angle 100W Type-C Adapter Extender for "
                     "Steam Deck, ROG Ally, Switch 2, Notebook Computers, "
                     "Thunderbolt 4, Tablet and Mobile Phones"),
        keywords=("USB-C, USB C, Type-C, right angle, right-angle, 90 degree, "
                  "elbow, adapter, extender, male to female, M-F, 100W, PD, "
                  "power delivery, Thunderbolt 4, strain relief, low profile, "
                  "Vanjua"),
        sold_by="FKtang-us",
        price_note=(
            "$6.99 for the pack of 4, qty 1, read from the order-details "
            "page — item line $6.99, Item(s) Subtotal $6.99, Shipping & "
            "Handling $0.00, Total before tax $6.99, Estimated tax $0.00, "
            "Rewards Points -$2.54, Grand Total $4.45.\n\n"
            "THIS IS THE EXACT TRAP THE TASK FILE DOCUMENTS. The confirmation "
            "email shows $4.45 and shows nothing about the $2.54 of rewards "
            "points that produced it. Booking the email total would have put "
            "these adapters in at 36% under what they cost. The ITEM LINE, "
            "$6.99, is the price. Read from the order-details page, which is "
            "the only sanctioned source for an Amazon item price.\n\n"
            "$6.99 is the PACK price and pack_quantity is 4, so InvenTree "
            "derives $1.7475 per piece itself. Do not pre-divide."
        ),
        notes=(
            "PACK OF 4, COUNTED IN PIECES. pack_quantity is 4 and the line "
            "quantity is 1 — one bag was bought, containing four adapters. "
            "The part NAME says nothing about the pack on purpose: stock is "
            "counted in pieces and the pack is a supplier fact. Written "
            "through .save() so pack_quantity_native is derived; a queryset "
            ".update() would set only the text field and leave the number "
            "receiving actually reads at 1.\n\n"
            "WHAT IT IS. A short right-angle USB-C elbow, male on one end and "
            "female on the other, that turns a straight cable through 90 "
            "degrees at the socket. Bought for clearance and strain relief — "
            "a plug that would otherwise stick straight out of a panel or a "
            "board edge. The 100W in the title is the vendor's stated power "
            "rating; it is transcribed, not verified, and no data rate is "
            "claimed by the title at all.\n\n"
            "DO NOT ASSUME IT PASSES DATA AT FULL SPEED. The title names "
            "Thunderbolt 4 as a compatible host, which is a compatibility "
            "claim and not a bandwidth spec. Cheap right-angle adapters "
            "routinely carry USB 2.0 data with full PD power. If one of these "
            "is going into a video or high-speed path, test it there before "
            "trusting it — a passing power test says nothing about the lanes. "
            "Caution to verify at the bench, not a measured fact.\n\n"
            "default_location deliberately EMPTY — nobody has said where USB "
            "adapters live, and default_location means where a SPARE goes "
            "home. Receiving takes an explicit --to.\n\n"
            "CATEGORY Electronics/Connectors/Adapters, with #729 (NRF24L01 "
            "socket adapter plate). It is a passive connector body, not a "
            "module — the flat Modules root holds several adapters (#477 "
            "HDMI-to-VGA, #134 USB-to-RS232) but those are active converters "
            "with silicon in them, which is the distinction being kept.\n\n"
            "Searched before creating across name/description/IPN/keywords/"
            "SKU on 26 terms (B0H3JNGX1D, USB-C, Type-C, 90 degree, right "
            "angle, male to female, adapter extender, Vanjua, 100W): 40-odd "
            "hits, all dev boards, end mills and countersinks matching '90 "
            "degree', and one worm-gear motor matching 'right angle'. Nothing "
            "is this. New part."
        ),
    ),
    dict(
        ref="113-6595171-3994627",
        asin="B07QB6KL85",
        price="6.54",
        qty="1",
        pack="5",
        arrives=date(2026, 9, 13),
        category="Electronics/Cables",
        name="Cable, USB-A to Micro-USB, 3 ft, USB 2.0",
        description=("orig: Amazon Basics 5-Pack USB-A to Micro USB Charging "
                     "Cable, 480Mbps Transfer Speed, Gold-Plated Plugs, USB "
                     "2.0, 3 Foot, Black"),
        keywords=("USB cable, USB-A, USB A, micro USB, micro-USB, micro B, "
                  "charging cable, data cable, USB 2.0, 480Mbps, 3 foot, 3 "
                  "ft, 1m, black, gold plated, Amazon Basics, Arduino, ESP32, "
                  "dev board, bench cable"),
        sold_by="Amazon Resale",
        price_note=(
            "$6.54 for the pack of 5, qty 1, read from the order-details "
            "page — item line $6.54, Item(s) Subtotal $6.54, Shipping & "
            "Handling $0.00, Total before tax $6.54, Estimated tax $0.00, "
            "Grand Total $6.54.\n\n"
            "Nothing is masked on this order: no rewards points, no coupon, "
            "no gift card. The line and the total agree. The LINE was still "
            "the source — whether they agree is not observable from the "
            "email, which is the whole reason the rule says read the order "
            "page. The other two orders in this same run both had a hidden "
            "adjustment.\n\n"
            "$6.54 is the PACK price and pack_quantity is 5, so InvenTree "
            "derives $1.308 per cable itself. Do not pre-divide."
        ),
        notes=(
            "BOUGHT USED. Sold by Amazon Resale, condition stated verbatim on "
            "the order-details page as 'Used - Very Good'. Recorded because "
            "it is invisible once the box is open and it changes what a "
            "failure means: a cable out of this pack that does not enumerate "
            "is a returned-stock cable, not a manufacturing defect, and it "
            "should be binned rather than puzzled over. Return window closes "
            "in the usual 30 days from delivery.\n\n"
            "PACK OF 5, COUNTED IN PIECES. pack_quantity is 5 and the line "
            "quantity is 1 — one pack was bought, containing five cables. The "
            "part NAME says nothing about the pack on purpose: stock counts "
            "pieces and the pack is a supplier fact. Written through .save() "
            "so pack_quantity_native is derived.\n\n"
            "WHAT IT IS FOR. Bench cabling for micro-USB dev boards — the "
            "Arduino Nano / Pro Micro / older ESP32 population on this "
            "instance (#258, #411, #281) is all micro-USB, and this is the "
            "consumable that goes with them. 3 ft, USB 2.0, 480 Mbps stated "
            "in the vendor title.\n\n"
            "480Mbps IS THE VENDOR'S CLAIM, TRANSCRIBED. It is also just the "
            "USB 2.0 signalling rate, which every compliant cable states and "
            "which says nothing about whether these particular used cables "
            "carry data at all — plenty of micro-USB cables are charge-only. "
            "If one is going on a board that needs to enumerate, plug it in "
            "and check before blaming the board.\n\n"
            "default_location deliberately EMPTY — nobody has said where "
            "bench USB cabling lives, and default_location means where a "
            "SPARE goes home. Receiving takes an explicit --to.\n\n"
            "CATEGORY Electronics/Cables, with #1145 (micro-HDMI to HDMI "
            "adapter cable) and the multi-conductor reels #1091-#1095. Not "
            "Electronics/Cables/Jumpers, which is specifically the ribbon "
            "jumper-wire sets #714-#717.\n\n"
            "Searched before creating across name/description/IPN/keywords/"
            "SKU on 26 terms (B07QB6KL85, micro USB, micro-USB, USB-A, "
            "charging cable, Amazon Basics, 480Mbps, USB 2.0): the hits were "
            "#258 a Pro Micro BOARD, #1176 AAA batteries matching 'Amazon "
            "Basics', and two USB-serial adapters. No USB cable of any kind "
            "is on the instance. New part."
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
