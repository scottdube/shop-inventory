"""Queue C for the 2026-09-02 08:40 daytime sweep — one Amazon PO.

Window swept: last-po-sweep 2026-09-01 minus 1 day = from 2026-08-31.

WHY ONLY ONE. The known-vendor Gmail pass returned nine threads and not one of
them was an order confirmation — all shipment notices, three "Delay in shipping"
notices, and Amazon Pharmacy. The single new order was found because the FIRST
Gmail query missed it: `subject:order` does NOT match Amazon's subject line
"Ordered: 1 Automotive item" (Gmail matches whole words, and "Ordered" is not
"order"). The order surfaced anyway off the order-history page, and a second
query with `subject:"Ordered"` confirmed it. Worth knowing for the next run:
the subject constraint the task file recommends can silently drop Amazon
confirmations. A tight `after:` date is the safer constraint for Amazon.

Everything else in the window, checked with one batched po_check call and
deliberately NOT imported here:

  113-8466709-7941016 -> PO-0156   111-4312729-1257045 -> PO-0155
  111-4901796-2449843 -> PO-0154   113-2527839-4777829 -> PO-0150
  113-3553954-0382657 -> PO-0151   113-4877215-5009041 -> PO-0152
  113-8727025-8809004 -> PO-0153   113-8690960-8633066 -> PO-0145

  112-5876133-0975416  Bounty paper towels, $28.49, Subscribe & Save.
                       `absent` from po_check, and left that way ON PURPOSE.
                       Household consumable on a 3-week auto-delivery, not a
                       shop part. Prior sweeps left it out too, so this is
                       existing practice being followed, not a new call.
  Amazon Pharmacy (Mounjaro, two threads) — medical. Suppressed, NOT
                       transcribed, per the standing rule.
  WEX benefits debit  — benefits card transaction confirmations, one of them
                       for AMZNPHARMA. Payment lines, and medical. Skipped.
  JLCPCB shipment     — known vendor, documented as NOT swept by section 3.
  USPS / UPS digests  — carrier notices, not purchases.

PRICE. $17.99, read from the order-details page, which is the only sanctioned
source. Item(s) Subtotal $17.99 == the item line == Grand Total, with $0.00
shipping, $0.00 tax, and NO rewards-points or gift-card line. Clean. This check
is not a formality: the same check on 111-4901796-2449843 yesterday caught a
$3.86 points deduction that would have understated the crimper by 11%.

PACK QUANTITY = 1, and it is the assortment rule, not laziness. The title says
"11PCS", but the eleven pieces are the dies, adapters, yoke and clamp of one
flaring set — they are not eleven interchangeable flaring tools. Per CLAUDE.md
an assortment is ONE unit; if the individual dies ever need to be findable the
kit becomes a LOCATION, not a pack quantity.

CATEGORY. Equipment/Hand Tools, matching where the Solsop crimper and the
ZOKYUYS terminal brush went yesterday. Not Tooling — that subtree is machine
tooling (holders, burs, jigs), and this is a hand tool.

ADJACENT EXISTING STOCK, cross-referenced in the notes but NOT merged: parts
#787 (Copper Tubing 3/16" OD x 5/32" ID, 5 ft) and #788 (Brass Tee Compression
Fitting 3/16" OD, 5 pack) are 3/16" line, which is squarely in this tool's
45-degree single/double flare range. Different items, so no duplicate — but
whoever reaches for the tool probably wants that tubing, and #787 is the only
brake-line-gauge tubing in the system.

No duplicate exists: `part_find.py flare brake tubing B0G32FPXFF DASBET`
returned 18 hits and not one is a flaring or tube-forming tool.
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
ISSUE = date(2026, 9, 1)
ARRIVES = date(2026, 9, 3)

RECEIVE_WARNING = (
    "*** ON RECEIVING, LOOK AT THIS LINE. *** receive_line_item() ignores "
    "pack_quantity and books the full pack price against a single piece. "
    "Check qty x price against the line's extended total before accepting."
)

ORDERS = [
    dict(
        ref="113-0934611-9763450",
        asin="B0G32FPXFF",
        price="17.99",
        pack="1",
        category="Equipment/Hand Tools",
        name="Brake Line Flaring Tool Kit, 45 deg single and double flare, 11 pc (DASBET)",
        description=("orig: DASBET 11PCS Flaring Tool Kit 45° Single & Double Brake Line "
                     "Flaring Tool"),
        keywords=("flaring tool, flare tool, brake line, brake line flaring, 45 degree "
                  "flare, single flare, double flare, SAE flare, tube flaring, tubing "
                  "tool, yoke, flaring dies, brake tubing, hydraulic line, automotive, "
                  "hand tool, DASBET"),
        sold_by="DASBETAUTO",
        price_note=(
            "$17.99 read from the order-details page. Item(s) Subtotal == item line "
            "== Grand Total, $0.00 shipping, $0.00 tax, and no rewards-points or "
            "gift-card line — nothing masked on this one. The order-details page is "
            "the source, never the order-history total: that total was wrong by "
            "$3.86 on the Solsop crimper in yesterday's batch."
        ),
        notes=(
            "ELEVEN PIECES, ONE UNIT — pack_quantity=1 on purpose. The \"11PCS\" in "
            "the vendor title counts the dies, adapters, yoke and clamp of a single "
            "flaring set, not eleven flaring tools. Per CLAUDE.md an assortment is "
            "one unit; if the individual dies ever need to be findable on their own, "
            "this becomes a LOCATION, not a pack quantity.\n\n"
            "Contents NOT itemised here — the vendor title states the count but not "
            "the die sizes, and nobody has opened the box. Fill in the actual die "
            "sizes at receipt rather than guessing them from the listing.\n\n"
            "GOES WITH, but is not a duplicate of:\n"
            "  #787  Copper Tubing 3/16\" OD x 5/32\" ID, 5 ft\n"
            "  #788  Brass Tee Compression Fitting 3/16\" OD (5 pack)\n"
            "3/16\" is squarely inside this tool's 45-degree single/double flare "
            "range, and #787 is the only brake-line-gauge tubing in the system. "
            "Whoever reaches for this tool probably wants that tubing too.\n\n"
            "No existing flaring or tube-forming tool was found before this part was "
            "created (searched flare / brake / tubing / ASIN / DASBET, 18 hits, none "
            "a flaring tool)."
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
        f"Amazon order {ref}, placed 2026-09-01, arriving {ARRIVES:%A %Y-%m-%d}.\n"
        f"Sold by: {o['sold_by']}.\n\n"
        f"{o['price_note']}\n\n"
        f"{o['notes']}\n\n"
        f"{RECEIVE_WARNING}"
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
