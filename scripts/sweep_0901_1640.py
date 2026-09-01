"""Queue C for the 2026-09-01 16:40 daytime sweep — three Amazon POs.

Window swept: last-po-sweep 2026-09-01 minus 1 day = from 2026-08-31.
All three were `absent` from po_check before this ran. Also in the window and
deliberately NOT imported:

  113-2527839-4777829 -> PO-0150   113-3553954-0382657 -> PO-0151
  113-4877215-5009041 -> PO-0152   113-8727025-8809004 -> PO-0153
  113-8690960-8633066 -> PO-0145   111-8717191-1899411 -> PO-0143
  Omnifixo #40098      — unknown vendor, no Company record; already on the
                         decision queue from the 12:46 run, not re-queued.
  Amazon Pharmacy, WEX — medical/benefits. Suppressed, NOT transcribed.
  YouTube Premium, Incogni — subscriptions, not parts.

PRICE, and this is the point of the run. The order-history page showed
$32.13 for the crimper. That is WRONG as an item price: the order-details page
reads Item(s) Subtotal $35.99 with a `Rewards Points: -$3.86` line beneath it.
$35.99 is what the tool cost. This is the exact failure the task file warns
about and it fired on 1 of 3 orders in a single window — the history total is
not a price, it is a payment. The other two read subtotal == line == grand
total with no points and no shipping.

THESE THREE ARE ONE JOB. Cable, lugs, shrink, a lug crimper and a terminal
brush bought within 40 minutes of each other. Recorded as three POs because
Amazon made three orders and the order number is the idempotency key, but the
notes cross-reference so whoever receives them puts them away together.

CRIMPER OVERLAP — flagged, not resolved. Part #138 is a BLIKA 10-ton HYDRAULIC
lug crimper with 9 dies, same AWG territory, and it reads `in stock = 0`. So
either it was never counted or it is gone, and this new Solsop is a different
mechanism at a fifth of the price. Not treated as a duplicate part (different
maker, mechanism, ASIN) but said out loud in the notes, because a redundant
$35.99 tool is worth ten seconds of Scott's attention while the return window
is open.

PACK QUANTITY. All three are pack_quantity=1, and one of them is a judgement:
  - The brush is titled "4 in 1". That names FUNCTIONS on a combination tool
    (inside post, outside post, terminal, small bore), not four loose brushes.
    But nobody has counted it, so it is 1 with the ambiguity written on the
    line rather than a guessed 4. Never invent a count.
  - The cable kit is an ASSORTMENT, not a multipack: 20 ft of wire + 10 lugs
    + tubing is ONE unit that arrives in one bag. Per CLAUDE.md an assortment
    is one unit; if its contents ever need to be findable it becomes a
    LOCATION, not a pack.

CATEGORY. Crimpers are split across the tree — #92 sits in Equipment/Hand
Tools while #138/#205/#228/#244/#337/#456 sit in Connectors, which is legacy
"seeded from purchase history" placement. Both tools here go to
Equipment/Hand Tools because that is what they are. The flat/nested
duplication itself is already a queued decision and is NOT half-fixed here.
The cable kit goes to Wire (#19), where the other bulk wire (#948) lives —
Electronics/Cables holds 24-28 AWG signal cable and 6 AWG welding cable is
not that.
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
ARRIVES = date(2026, 9, 2)

RECEIVE_WARNING = (
    "*** ON RECEIVING, LOOK AT THIS LINE. *** receive_line_item() ignores "
    "pack_quantity and books the full pack price against a single piece. "
    "Check qty x price against the line's extended total before accepting."
)

SIBLINGS = (
    "PART OF ONE JOB — three Amazon orders placed within 40 minutes on "
    "2026-09-01, all battery-cable work:\n"
    "  113-4901796-2449843  Solsop lug crimper, AWG 10-1/0\n"
    "  111-4312729-1257045  FASTSTORM 6 AWG cable + lugs + shrink kit\n"
    "  113-8466709-7941016  ZOKYUYS battery terminal brush\n"
    "Put them away together."
)

ORDERS = [
    dict(
        ref="111-4901796-2449843",
        asin="B0FD2MGBZV",
        price="35.99",
        pack="1",
        category="Equipment/Hand Tools",
        name="Battery Cable Lug Crimper, AWG 10-1/0 (Solsop)",
        description=("orig: Solsop Battery Cable Crimper Tool for AWG 10, 8, 6, 4, 2, "
                     "1/0 Gauge"),
        keywords=("crimper, crimping tool, lug crimper, battery cable crimper, "
                  "cable lug, ring terminal, hammer crimper, AWG 10, AWG 8, AWG 6, "
                  "AWG 4, AWG 2, 1/0, welding cable, battery cable, Solsop"),
        sold_by="Solsop-US",
        price_note=(
            "*** PRICE TRAP FIRED ON THIS ORDER. *** The order-history page shows "
            "$32.13. That is NOT the item price — it is what was charged after "
            "$3.86 of rewards points. The order-details page reads:\n"
            "    Item(s) Subtotal:  $35.99\n"
            "    Rewards Points:    -$3.86\n"
            "    Grand Total:       $32.13\n"
            "$35.99 is the cost basis and is what is recorded here."
        ),
        notes=(
            "Single tool, no pack.\n\n"
            "OVERLAPS AN EXISTING PART — worth a look while the return window is "
            "open. Part #138 is a BLIKA 10-ton HYDRAULIC lug crimper with 9 dies "
            "covering the same gauge range, and it currently reads in stock = 0, "
            "so it was either never counted or it is no longer here. This Solsop "
            "is a different mechanism at roughly a fifth of the price, so it was "
            "NOT merged into #138 — but if the BLIKA is on the bench, this is a "
            "duplicate capability.\n\n" + SIBLINGS
        ),
    ),
    dict(
        ref="111-4312729-1257045",
        asin="B0FT8BQNVS",
        price="37.99",
        pack="1",
        category="Wire",
        name='Battery Cable Kit, 6 AWG, 10 ft black + 10 ft red, with 10 lugs and heat shrink',
        description=('orig: FASTSTORM 6 AWG Battery Cable, 10 Feet Black + 10Feet Red '
                     'Flexible 6 Gauge Wire with 5pcs of 5/16" & 5pcs 3/8" Tinned Copper '
                     'Lugs Terminal Welding Cable + Heat Shrink Tubing for Auto Solar '
                     'Marine RV'),
        keywords=("battery cable, welding cable, 6 AWG, 6 gauge, flexible cable, "
                  "tinned copper, cable lug, ring terminal, 5/16 lug, 3/8 lug, "
                  "heat shrink, automotive, solar, marine, RV, red, black, FASTSTORM"),
        sold_by="FASTSTORM",
        price_note=(
            "$37.99 read from the order-details page. Item(s) Subtotal == item line "
            "== Grand Total, $0.00 shipping, $0.00 tax, no points or gift-card line — "
            "nothing masked on this one. The page is still the source, never the "
            "order-history total (which was wrong by $3.86 on the crimper in this "
            "same batch)."
        ),
        notes=(
            "ASSORTMENT, NOT A MULTIPACK — pack_quantity=1. One kit, one price. "
            "Contents stated verbatim in the vendor title:\n"
            "  - 10 ft 6 AWG flexible cable, BLACK\n"
            "  - 10 ft 6 AWG flexible cable, RED\n"
            "  - 5 x tinned copper lugs, 5/16 in stud\n"
            "  - 5 x tinned copper lugs, 3/8 in stud\n"
            "  - heat shrink tubing (quantity and sizes not stated — do not assume)\n\n"
            "Per CLAUDE.md an assortment is ONE unit, not 20-plus interchangeable "
            "pieces. If the lugs ever need to be findable on their own this becomes "
            "a LOCATION, not a pack quantity.\n\n"
            "ADJACENT EXISTING PART, not a duplicate: #137 is a lugs-only assortment "
            "kit (AWG 2/4/6/8/10) in Consumables/Solder. This one is mostly cable.\n\n"
            + SIBLINGS
        ),
    ),
    dict(
        ref="113-8466709-7941016",
        asin="B0DCVTTXMJ",
        price="6.59",
        pack="1",
        category="Equipment/Hand Tools",
        name="Battery Terminal Cleaning Brush, 4-in-1 post and terminal cleaner",
        description=("orig: ZOKYUYS 4 in 1 Car Battery Cleaning Brush,Anti-Corrosion "
                     "Battery Terminals,Copper Pipes Cleaner Brush Tool,Universal for "
                     "Automotive and Marine for Plumbing Installation Soldering Brazing"),
        keywords=("battery brush, terminal brush, post cleaner, battery terminal "
                  "cleaner, anti-corrosion, copper pipe cleaner, fitting brush, "
                  "plumbing brush, soldering prep, brazing prep, wire brush, "
                  "automotive, marine, ZOKYUYS"),
        sold_by="jinheantongltd",
        price_note=(
            "$6.59 read from the order-details page. Item(s) Subtotal == item line "
            "== Grand Total, $0.00 shipping, $0.00 tax, no points line."
        ),
        notes=(
            "COUNT IS NOT VERIFIED — pack_quantity=1 on purpose. The title says "
            "\"4 in 1\", which on this class of tool names four FUNCTIONS on one "
            "combination body (inside post, outside post, terminal, small bore), "
            "not four loose brushes. Nobody has counted it, so it is recorded as 1 "
            "with the ambiguity stated rather than a guessed 4. If four separate "
            "brushes arrive, fix pack_quantity at receipt.\n\n"
            "Doubles as a copper-pipe fitting brush for solder/braze prep, per the "
            "vendor title — that is why it is a hand tool and not a battery-only "
            "consumable.\n\n" + SIBLINGS
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
