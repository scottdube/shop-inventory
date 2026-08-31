"""Queue C for the 2026-08-30 22:40 daytime sweep — four Amazon POs.

Window swept: last-po-sweep 2026-08-30 minus 1 day = from 2026-08-29.
All four were `absent` from po_check before this ran. Also in the window and
deliberately NOT imported:

  113-8690960-8633066  -> PO-0145   (08-27 22:40 sweep)
  111-8717191-1899411  -> PO-0143   (08-26 13:15 sweep)
  111-4846191-6220252  -> PO-0144   (same)
  112-5876133-0975416  Bounty paper towels — household consumable, skipped,
                       already sitting on the decision queue awaiting a ruling.
  113-1545085-3620205  CANCELLED by Amazon — nothing bought, no PO.
  113-8789992-1384241  $0.00 label printer — on the decision queue since the
                       16:40 run as a cost-basis call. Not re-queued here.

PRICE. All four order-details pages read Item(s) Subtotal == item line ==
Grand Total, with $0.00 shipping and $0.00 tax and no gift-card or points
line. So unusually there is no rewards masking to unwind this time — but the
prices were still read from the order-details pages, never from the email or
the order-history total, because the history total is the same field that read
$4.28 against $16.48 of real items once before.

CATEGORY. The dupe probe surfaced TWO parallel homes for every one of these
concepts: flat legacy ("Switches" #33, "Sensors" #21, "Relays" #15, all
"seeded from purchase history") and nested ("Electronics/Electromechanical/
Switches" #111, "Electronics/Sensors" #64). The 30 most recently created parts
settle it — #1161 Electronics/Connectors, #1160 Electronics/Power, #1148
Electronics/Modules, #1145 Electronics/Cables, #1143 Electronics/Power — the
nested tree is current practice, so these four go there. The flat/nested
duplication itself is a data-quality problem bigger than this import and is on
the decision queue rather than being silently half-fixed here.

PACK QUANTITY. Two of the four are multi-packs whose count is stated verbatim
in the vendor title, so the count is a fact and not an interpretation:
"3pcs" -> pack_quantity 3, "2pcs" -> pack_quantity 2. Following the HGR15
precedent, each line is qty 1 at the ONE price that appears on the order; no
derived per-piece price is invented. Both carry the receive warning below.

*** receive_line_item() ignores pack_quantity and books the whole pack price
against a single piece. Whoever checks these in must look. ***

COLOUR, on the push buttons. The 3-pack is one red, one yellow and one green
button. They are one supplier SKU but they are NOT interchangeable in use —
a green start and a red stop are different things on a panel. Left as one part
with pack_quantity 3 because that is what was bought and what will arrive;
splitting into three parts is a call for whoever receives them, and it is
said in the PO notes so the decision is made with the parts in hand rather
than guessed at here.
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
ISSUE = date(2026, 8, 30)

RECEIVE_WARNING = (
    "*** ON RECEIVING, LOOK AT THIS LINE. *** receive_line_item() ignores "
    "pack_quantity and books the full pack price against a single piece. "
    "Check qty x price against the line's extended total before accepting."
)

ORDERS = [
    dict(
        ref="113-2527839-4777829",
        asin="B07GPJ6876",
        price="14.99",
        pack="3",
        target=date(2026, 9, 1),
        category="Electronics/Electromechanical/Switches",
        name="Push Button Switch, 22 mm panel mount, momentary, 1NO+1NC, 10 A (LA38-11BNRYG)",
        description=("orig: Taiss 3pcs 22mm Momentary Push Button Switch 10A 440V 1NO 1NC "
                     "Red Yellow Green Sign DPST Pushbutton Switches LA38-11BNRYG"),
        keywords=("push button, pushbutton, momentary, 22 mm, panel mount, LA38, "
                  "LA38-11BNRYG, 1NO 1NC, normally open, normally closed, 10 A, "
                  "control panel, start stop, red, yellow, green, Taiss"),
        sold_by="SEA-GULL",
        notes=("PACK: 3 buttons, one RED one YELLOW one GREEN. pack_quantity=3 on the "
               "SupplierPart; the line is qty 1 at the $14.99 that appears on the order.\n\n"
               "THE THREE ARE NOT INTERCHANGEABLE. Colour is functional on a panel "
               "(green start, red stop). If colour ends up mattering, split this into "
               "three parts at receipt — decided with the buttons in hand, not guessed "
               "here.\n\n" + RECEIVE_WARNING),
    ),
    dict(
        ref="113-3553954-0382657",
        asin="B0H28L84GL",
        price="17.99",
        pack="2",
        target=date(2026, 9, 1),
        category="Electronics/Sensors",
        name='Water Flow Sensor YF-S401, Hall effect, 0.3-3 L/min, 1/4" quick connect',
        description=('orig: Yuuhseel 2pcs YF - S401 1/4" Quick Connect Hall Effect '
                     "0.3-3L / min Flow Rate Control Water Flow Sensor Flow Meter for "
                     "Water Coolers/Coffee Machines/Water Purifiers"),
        keywords=("flow sensor, flow meter, water flow, YF-S401, YF-S, hall effect, "
                  "hall sensor, pulse output, 0.3-3 L/min, quarter inch, quick connect, "
                  "coolant flow, coolant interlock, liquid cooling, Yuuhseel"),
        sold_by="Yuuhseel",
        notes=("PACK: 2 identical sensors, count stated verbatim in the vendor title. "
               "pack_quantity=2 on the SupplierPart; the line is qty 1 at the $17.99 "
               "that appears on the order — no derived per-piece price.\n\n"
               + RECEIVE_WARNING),
    ),
    dict(
        ref="113-4877215-5009041",
        asin="B0GX5HM4X3",
        price="15.99",
        pack="1",
        target=date(2026, 9, 3),
        category="Electronics/Sensors",
        name="INA228 Current/Voltage/Power Monitor Breakout, 20-bit I2C",
        description=("orig: INA228 High Precision Current Voltage Power Monitor Sensor "
                     "Module for Measuring Voltage Current"),
        keywords=("INA228, current sensor, current monitor, voltage monitor, power monitor, "
                  "energy monitor, shunt, high side, I2C, 20-bit, precision, "
                  "breakout, module, TI, Texas Instruments"),
        sold_by="DIY-Module",
        notes="Single module, no pack. Price read from the order-details page.",
    ),
    dict(
        ref="113-8727025-8809004",
        asin="B0B4CBZCBC",
        price="31.16",
        pack="1",
        target=date(2026, 9, 1),
        category="Electronics/Electromechanical",
        name="Magnetic Contactor MC-9b, 3 pole, 25 A Ith, 24 VDC coil",
        description=("orig: BAOMAIN 3 Pole Magnetic Contactor,25A Ith 24V DC Coil,MC-9b,"
                     "UL Certified"),
        keywords=("contactor, magnetic contactor, motor contactor, MC-9b, MC-9, 3 pole, "
                  "three phase, 25 A, Ith, 24 VDC coil, 24V DC, UL, DIN rail, "
                  "motor starter, Baomain"),
        sold_by="Baomain",
        notes=("Single unit, no pack. Price read from the order-details page.\n\n"
               "COIL IS 24 VDC, not line voltage — it needs a 24 V supply to pull in. "
               "Noted because a contactor's coil voltage is the one spec that makes it "
               "the wrong part, and it is not in the part name of most catalogue entries."),
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
                raise SystemExit(f"refusing to create: part with {field}={value!r} exists (#{dupe.pk})")

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
        check = Part.objects.get(pk=p.pk)          # silent-save trap: re-read
        assert check.name == o["name"] and check.IPN == asin, f"part {p.pk} did not stick"
        assert check.keywords, f"part {p.pk} lost its keywords"
        print(f"CREATE part {check.pk}: {check.name[:60]}  cat={check.category.pathstring}")

        sp = SupplierPart.objects.create(
            supplier=AMAZON, part=p, SKU=asin, pack_quantity=o["pack"],
        )
        fresh = SupplierPart.objects.get(pk=sp.pk)
        assert fresh.SKU == asin, f"supplierpart {sp.pk} did not stick"
        print(f"CREATE SupplierPart {fresh.pk}: {asin} pack_quantity={fresh.pack_quantity}")
        sp = fresh

    notes = (
        f"Amazon order {ref}, placed 2026-08-30, arriving {o['target']:%A %Y-%m-%d}.\n"
        f"Sold by: {o['sold_by']}.\n\n"
        f"PRICE ${o['price']} read from the order-details page, NOT from the email or "
        "the order-history total. This order showed Item(s) Subtotal == item line == "
        "Grand Total with no gift-card or rewards line, so nothing was masked — but "
        "the page is still the source.\n\n"
        + o["notes"]
    )

    po = PurchaseOrder.objects.create(
        reference=PurchaseOrder.generate_reference(),
        supplier=AMAZON,
        supplier_reference=ref,
        description=f"Amazon order {ref}",
        notes=notes,
        issue_date=ISSUE,
        target_date=o["target"],
    )
    po.status = PurchaseOrderStatus.PLACED.value
    po.save()

    po = PurchaseOrder.objects.get(pk=po.pk)
    assert po.supplier_reference == ref, "PO supplier_reference did not stick"
    assert po.issue_date == ISSUE, "PO issue_date did not stick"
    assert po.target_date == o["target"], "PO target_date did not stick"
    assert po.status == PurchaseOrderStatus.PLACED.value, f"PO status is {po.status}, not PLACED"
    print(f"CREATE {po.reference}  status=PLACED  supplier_reference={po.supplier_reference}")

    li = PurchaseOrderLineItem.objects.create(
        order=po, part=sp, quantity=Decimal("1"), purchase_price=Decimal(o["price"]),
    )
    li = PurchaseOrderLineItem.objects.get(pk=li.pk)
    assert li.purchase_price.amount == Decimal(o["price"]), f"line {li.pk} price did not stick"
    print(f"LINE {li.pk}: {sp.part.name[:55]} qty={li.quantity} unit={li.purchase_price}")

    created.append((po.reference, ref, po.pk))

print("=" * 72)
for reference, ref, pk in created:
    print(f"{reference}  {ref}  {base}/order/purchase-order/{pk}/")
print(f"{len(created)} PO(s) created, all left in PLACED — nothing received, no stock made.")
