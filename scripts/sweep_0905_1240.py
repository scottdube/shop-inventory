"""Queue C for the 2026-09-05 12:40 daytime sweep — two Amazon POs, both CAN.

Window swept: last-po-sweep 2026-09-05 minus 1 day = from 2026-09-04.

WHAT WAS IN THE WINDOW. Thirteen known-vendor threads. Eleven were not orders:
four Amazon marketing blasts, one shipment notice, one review solicitation, one
RETURN confirmation, two AliExpress delivery nags on order 8213410090395753
(already PO-0147, Complete), one Pololu Labor Day sale, one Walmart CANCELATION
confirmation. Two were real confirmations, both placed TODAY at 11:46 and 12:06
EDT — i.e. AFTER the 08:46 sweep ran, which is the whole argument for running
this job four times a day instead of once.

  113-2212001-1602645 -> absent   <- imported here
  113-2286014-7906656 -> absent   <- imported here
  113-4088575-5438644 -> PO-0158  (09-03 sweep)
  8213410090395753    -> PO-0147  (Complete)

THE SUBJECT-LINE TRAP, AGAIN. A `subject:order OR subject:confirmation` pass
returned exactly TWO threads and MISSED BOTH of these. Gmail matches whole
words, and the Amazon confirmation subject is "Ordered: N Electronics items" —
"Ordered" != "order". Documented by the 09-02 08:40 sweep and re-documented by
09-03. The pass that found them was date-only, `after:2026/09/04` across the
known-vendor sender list, with no subject constraint at all. On a one-day window
that is 13 threads, which is cheap; the subject constraint only earns its keep
on a window wide enough for the marketing volume to swamp the orders.

PRICES read from the order-details pages, the only sanctioned Amazon source, and
the second order is exactly why that rule exists:

  113-2212001-1602645  subtotal $21.98 == grand total $21.98, ship $0, tax $0.
                       Nothing masked. Line reads 2 @ $10.99.
  113-2286014-7906656  item line $24.99, subtotal $24.99 — but Grand Total
                       $15.81, because a REWARDS POINTS line takes off $9.18.
                       The email states only the $15.81. Booking that would have
                       understated the adapter by 37%.

That is the second live catch of an invisible points deduction in four sweeps
(the Solsop crimper was the first, $3.86). The rule is not ceremony.

PACK QUANTITY = 1 on both, and both were checked rather than defaulted. The
Waveshare listing sells ONE board per unit — qty 2 on the order is two units at
$10.99 each, not one 2-pack — and the Jhoinrch adapter is a single dongle.
Neither title states a piece count, which is the usual tell for a real multipack.

THE WAVESHARE BOARD IS NOT A NEW PART. #19 "SN65HVD230 CAN Transceiver Module"
already exists (stock 6, from the hiBCTR 3-pack, SKU B0FDLDXCK9). Same silicon,
same form factor — a 3.3V SN65HVD230 CAN transceiver breakout — so this gets a
SECOND SupplierPart under #19 rather than a lookalike part, which is the
duplicate-before-create rule doing its job. Contrast the PCF8574 case on
2026-09-03, where an LCD backpack built AROUND the chip correctly stayed
separate: a module is not its IC, but two vendors' boards of the SAME module ARE
the same part.

WORTH KNOWING WHILE READING #19's STOCK: Amazon confirmed a RETURN of the hiBCTR
3-pack on 2026-09-04 (drop-off by Sep 16). So the 6 pieces on that row are not
all staying, and this order looks like the replacement. NO stock was touched
here — receiving and returns are both a human's job — but it is on the decision
queue so the row does not quietly go wrong.

CATEGORY for the adapter: Modules/Interface, matching #76 FT232RL USB-TTL and
#77 CP2102 USB-TTL — the same shape of thing, a USB bus-converter dongle — and
#954, the shop-built Teensy/MCP2562 CAN interface. NOT the ICs tree where #19
sits: #19 is a bare-ish transceiver breakout, this is a finished instrument.

Both POs left in PLACED. Nothing received, no stock created.
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
ISSUE = date(2026, 9, 5)
ARRIVES = date(2026, 9, 6)

ORDERS = [
    dict(
        ref="113-2212001-1602645",
        asin="B00KM6XMXO",
        price="10.99",
        qty="2",
        pack="1",
        existing_part=19,
        sold_by="waveshare",
        price_note=(
            "$10.99 per board, read from the order-details page. Item(s) Subtotal "
            "$21.98 == 2 x $10.99 == Grand Total $21.98; shipping $0.00, tax $0.00, "
            "and NO rewards-points or gift-card line, so nothing is masked. The line "
            "below is priced PER BOARD with qty 2, not one 2-pack at $21.98 — the "
            "Waveshare listing sells a single board per unit."
        ),
        notes=(
            "SECOND SUPPLIER FOR #19, NOT A NEW PART. #19 SN65HVD230 CAN Transceiver "
            "Module already carries SKU B0FDLDXCK9 (hiBCTR, 3-pack). This is the same "
            "component identity — a 3.3V SN65HVD230 CAN transceiver breakout — from a "
            "different vendor, so it attaches as another SupplierPart. Two vendors' "
            "boards of the same module are the same part; that is not the same "
            "question as the PCF8574/LCD-backpack case, where a module built around a "
            "chip correctly stayed separate from the chip.\n\n"
            "THE hiBCTR 3-PACK IS BEING RETURNED. Amazon confirmed a return request "
            "on 2026-09-04, drop-off by Sep 16, for the hiBCTR 3-Pack SN65HVD230. #19 "
            "reads stock 6 as of this import and NO stock was touched here. Whoever "
            "checks the return out needs to take those pieces off the row, and this "
            "order is very likely the replacement. On the decision queue.\n\n"
            "WHAT IT IS. TI SN65HVD230: 3.3V CAN transceiver, up to 1 Mbps, with a "
            "slope-control/standby mode pin. The Waveshare board adds the 120R "
            "termination (usually jumper-selectable — CHECK THE JUMPER before hanging "
            "it mid-bus; a stub with termination on is a classic reason a bus that "
            "worked with two nodes stops working with three).\n\n"
            "3.3V PART. It does not tolerate a 5V bus controller driving TXD without "
            "thought. The 5V equivalent on hand is #798 MCP2562-E/P (DIP-8), and #954 "
            "is the shop-built Teensy 3.2 + MCP2562 interface board.\n\n"
            "Searched before creating (SN65HVD230 / B00KM6XMXO / CAN / adapter): "
            "#19 is the match, reused."
        ),
    ),
    dict(
        ref="113-2286014-7906656",
        asin="B0FSVNBKQ4",
        price="24.99",
        qty="1",
        pack="1",
        category="Modules/Interface",
        name="USB to CAN FD Adapter, isolated, 5 Mbps",
        description=("orig: Jhoinrch Isolation USB to CAN FD Adapter Converter Up "
                     "to 5Mbps"),
        # Part.keywords is capped at 250 characters and Part.save() calls
        # full_clean(), so an over-long list is a hard ValidationError.
        keywords=("USB-CAN, USB to CAN, CAN FD, CANFD, CAN bus, CAN analyser, bus "
                  "sniffer, isolated, galvanic isolation, 5Mbps, OBD, automotive bus, "
                  "candump, SocketCAN, python-can, adapter, dongle, interface, "
                  "Jhoinrch, diagnostics"),
        sold_by="Johinrch",
        price_note=(
            "$24.99, read from the order-details page — item line $24.99, Item(s) "
            "Subtotal $24.99, shipping $0.00, tax $0.00.\n\n"
            "THE EMAIL SAYS $15.81 AND THE EMAIL IS WRONG TO USE. The order page "
            "carries a Rewards Points line of -$9.18, which is why Grand Total reads "
            "$15.81. Points are a payment method, not a discount; the adapter cost "
            "$24.99. Booking the email figure would have understated it by 37% and "
            "would have quietly poisoned any future 'what did this cost' question. "
            "Second live catch of a masked Amazon total in four sweeps."
        ),
        notes=(
            "WHAT IT IS. USB-to-CAN FD adapter with galvanic isolation, rated to "
            "5 Mbps on the data phase. CAN FD, not just classic CAN — it will talk to "
            "a classic 1 Mbps bus, but the reverse is not true, so this is the one to "
            "reach for on anything modern.\n\n"
            "ISOLATION IS THE POINT, not a bonus feature. It is what lets a laptop sit "
            "on a vehicle or machine bus without tying the laptop ground to the "
            "machine ground. Do not substitute a non-isolated dongle for it and assume "
            "the same safety.\n\n"
            "FILED AS A MODULE, NOT AN IC. Same shelf question as #76 (FT232RL "
            "USB-TTL) and #77 (CP2102 USB-TTL) — a finished USB bus-converter you plug "
            "in — rather than the transceiver silicon in #19/#798.\n\n"
            "BOUGHT ALONGSIDE two Waveshare SN65HVD230 boards on the same day "
            "(PO for order 113-2212001-1602645). The pair reads as one CAN bring-up: "
            "the adapter is the host end, the transceivers are the node end. The "
            "shrink-fit induction machine (#782) is the project on file that calls for "
            "isolated CAN supervision of the rectifier.\n\n"
            "Searched before creating (\"USB to CAN\" / \"CAN FD\" / B0FSVNBKQ4 / CAN / "
            "adapter): no USB-CAN interface of any kind existed, 0 hits on both "
            "specific terms."
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
        if o.get("existing_part"):
            # Same component identity as a part we already hold; attach a second
            # supplier rather than creating a lookalike.
            p = Part.objects.get(pk=o["existing_part"])
            print(f"reuse  part {p.pk}: {p.name}  (adding a second supplier)")
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
