"""Queue C for the 2026-09-06 08:40 daytime sweep — one Amazon PO, AAA cells.

Window swept: last-po-sweep 2026-09-05 minus 1 day = from 2026-09-04.

WHAT WAS IN THE WINDOW. Five Amazon orders on the history page from 09-04 on,
plus four AliExpress threads and two non-vendor purchase-category hits. Checked
as one batch through po_check.py, which is the idempotency gate:

  113-8216914-9857847  absent   <- imported here (AAA cells)
  112-7129057-7302625  absent   <- SKIPPED, see below
  113-2212001-1602645  PO-0159  (09-05 12:40 sweep)
  113-2286014-7906656  PO-0160  (09-05 12:40 sweep)
  113-4088575-5438644  PO-0158  (09-03 sweep)
  8213410090395753     PO-0147  (Complete)
  8213410090415753     PO-0146  (Complete)

SKIPPED, AND WHY IT IS A JUDGEMENT CALL AND NOT A RULE. Order
112-7129057-7302625, Jack Link's Original Beef Jerky 2-pack, $21.19, a
Subscribe & Save auto-delivery. The task file's skip list names apparel,
memberships and payment lines; it does NOT name groceries, so this is not
covered by an existing rule. Skipped anyway: it is food on a household
subscription, it will never be stocked, counted or consumed as a shop part, and
importing it would put a part in the tree that no future stock question can ever
be asked about. Flagged in the report rather than silently dropped. The same
call would apply to the household paper goods that show up on the Buy-It-Again
rail. If Scott wants groceries in, the fix is a one-line skip-list edit, not a
re-litigation of this order.

TWO NON-AMAZON PURCHASES WERE FOUND AND NEITHER BECAME A PO:
  * geeksoutfit.com GK281233, five T-shirts, $103.95 — APPAREL, suppressed by
    rule. vendor_triage.py agreed (suppress: apparel).
  * omnifixo.com #40098, OF-M4.4 helping-hands, $69.00 + $7.00 shipping —
    unknown vendor, no Company record, so no auto-PO by standing rule.
    vendor_triage.py reports it ALREADY QUEUED on the decision queue, so no
    duplicate decision was added. Worth knowing when that decision is answered:
    Omnifixo is a REPEAT vendor, not a one-off — order #12443 dates from
    2023-08-15.

PRICE: $13.70, read from the order-details page, which is the only sanctioned
Amazon source. The item line reads $13.70 and Item(s) Subtotal is $13.70.
Grand Total is $11.64 because a SUBSCRIBE & SAVE line takes off $2.06 — an
ORDER-level discount, not a line price. This is the same class of trap as the
rewards-points deductions caught on 09-01 and 09-05, but it runs the other way:
here the email's total is LOWER than the line, so booking $11.64 would have
UNDERSTATED the cells by 15%. Shipping $0.00, tax $0.00, nothing else masked.

PACK QUANTITY = 36, AND THIS IS THE WHOLE POINT OF THE ORDER. One purchased unit
is a 36-count box of interchangeable AAA cells, so stock counts 36 pieces and
the supplier part carries the 36. Left at InvenTree's default of 1 this would
book $13.70 per cell instead of $0.3806 — exactly the failure that read 19
storage bins at $208.62 each. It is a genuine multipack and not an assortment:
36 identical LR03 cells, one value, fully interchangeable, so it does NOT become
a location the way a 24-value capacitor kit does.

NAME CARRIES NO PACK COUNT, deliberately. "If a part NAME says '10 pack' while
its quantity counts pieces, the name is the bug." The 36 lives on the
SupplierPart, where receiving reads it.

CATEGORY Electronics/Power, following the only battery precedent on the
instance — #793 LiPo Battery 3.7V 750mAh, which sits there. Not Consumables:
that tree is solder and shop supplies, and a cell is a power source that other
parts designate, which is what makes it findable from a project.

default_location left EMPTY on purpose. The rule is that default_location is
where a SPARE goes home, and nobody has told this job where AAA cells live. A
guess here would be a lie that survives; the receive step takes an explicit
--to. NOT on the decision queue — it resolves itself the moment someone checks
the box in.

Searched before creating (AAA / alkaline / battery / B00LH3DMUO): 13 hits on
"battery", every one of them a battery CABLE, LUG, CRIMPER, TERMINAL BRUSH,
contact plate or a device that contains a battery. Zero primary cells of any
chemistry or size. The single "AAA" hit was #161, a fish scale, matching on its
description. This is a new part.

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
ISSUE = date(2026, 9, 6)
ARRIVES = date(2026, 9, 21)

ORDERS = [
    dict(
        ref="113-8216914-9857847",
        asin="B00LH3DMUO",
        price="13.70",
        qty="1",
        pack="36",
        category="Electronics/Power",
        name="Alkaline Battery AAA 1.5V (LR03)",
        description=("orig: Amazon Basics AAA Long-Lasting Alkaline Batteries, "
                     "36-Count, 1.5 Volt, Reliable Performance, 10-Year Shelf "
                     "Life, Emergency Storage"),
        # Part.keywords is capped at 250 characters and Part.save() calls
        # full_clean(), so an over-long list is a hard ValidationError.
        keywords=("AAA, LR03, R03, MN2400, triple A, alkaline, primary cell, "
                  "battery, batteries, 1.5V, 1.5 volt, non-rechargeable, "
                  "disposable, remote, caliper, DRO, test meter, torch, "
                  "flashlight, consumable, Amazon Basics"),
        sold_by="Amazon.com",
        price_note=(
            "$13.70 for the 36-count box, read from the order-details page — item "
            "line $13.70, Item(s) Subtotal $13.70, Shipping & Handling $0.00, "
            "Estimated tax $0.00.\n\n"
            "THE EMAIL SAYS $11.64 AND THE EMAIL IS WRONG TO USE. The order page "
            "carries a Subscribe & Save line of -$2.06, which is why Grand Total "
            "reads $11.64. That is an ORDER-level discount on a recurring "
            "delivery, not the price of the goods. Same class as the rewards-points "
            "catches on 09-01 and 09-05, but running the OTHER WAY: here the total "
            "is lower than the line, so the email figure would have understated "
            "the cells by 15%.\n\n"
            "PER CELL: $13.70 / 36 = $0.3806. That division is done by "
            "pack_quantity at receive time, NOT written here — the line below is "
            "one purchased unit at the pack price, which is what the order says."
        ),
        notes=(
            "PACK OF 36, AND THE 36 IS ON THE SUPPLIER PART WHERE RECEIVING READS "
            "IT. One purchased unit is a 36-count box; stock counts individual "
            "cells. Left at the default pack_quantity of 1 this books $13.70 per "
            "cell — the 19-storage-bins failure ($208.62 instead of $20.86) in its "
            "purest form. pack_quantity_native is asserted against pack_quantity "
            "below, because only native is read at receive time and a queryset "
            "update would set the text and not the number.\n\n"
            "A MULTIPACK, NOT AN ASSORTMENT. 36 identical LR03 cells, one value, "
            "fully interchangeable — so it is a pack. Contrast a 24-value "
            "capacitor kit, which is ONE unit and becomes a location if its "
            "contents must be findable.\n\n"
            "WHAT IT IS. Standard AAA (IEC LR03 / ANSI 24A) alkaline primary cell, "
            "1.5 V nominal, stated 10-year shelf life. NOT rechargeable — do not "
            "put these on a NiMH charger. Note that NiMH AAA cells are 1.2 V "
            "nominal, so anything that browns out on rechargeables wants these, "
            "and anything that leaks over a long idle period wants the "
            "rechargeables instead. Alkaline cells vent potassium hydroxide when "
            "left flat in a device for months; the usual victims are instruments "
            "that sit unused between jobs.\n\n"
            "AUTO-DELIVERED EVERY 6 MONTHS on Subscribe & Save. This PO will "
            "therefore recur on its own without anyone ordering it. That is worth "
            "knowing before someone reads a future duplicate as a mistake: it is "
            "the subscription, and the supplier_reference will differ each time.\n\n"
            "default_location deliberately EMPTY — nobody has said where AAA cells "
            "live, and default_location means where a SPARE goes home. Receiving "
            "takes an explicit --to.\n\n"
            "Searched before creating (AAA / alkaline / battery / B00LH3DMUO): "
            "13 hits on 'battery' and every one is a battery CABLE, LUG, CRIMPER, "
            "TERMINAL BRUSH, contact plate, or a device containing a battery. Zero "
            "primary cells of any chemistry. The one 'AAA' hit was #161, a fish "
            "scale. New part."
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
