"""Queue C for the 2026-09-09 16:40 daytime sweep — one Amazon PO, a power splitter.

Window swept: last-po-sweep 2026-09-09 minus 1 day = from 2026-09-08.

WHAT WAS IN THE WINDOW. Three vendor order references, checked as one batch
through po_check.py, which is the idempotency gate:

  113-7332958-8875426  absent   <- imported here (Cablelera power splitter)
  8214467898875753     PO-0148  (Complete)
  8214467898895753     PO-0149  (Complete)

The two AliExpress numbers are already in and are only in the window because
AliExpress sent "how did it go?" / "awaiting confirmation" nags for orders that
were imported days ago. Neither is new work.

THE GMAIL SEARCH ALMOST MISSED THIS ORDER, and that is worth writing down. A
from:-plus-subject: search over the known itemised vendors returned five threads
and NONE of them was the confirmation for 113-7332958-8875426, even though the
subject is literally "Ordered: 2 Electrical & Heating items" and the sender is
auto-confirm@amazon.com. Gmail did not match `subject:order` against "Ordered:".
It was found because the Amazon ORDER HISTORY PAGE was read first and the order
was visible there, then confirmed by a narrower search on `subject:Ordered`.
Standing lesson: the order history page is the ground truth for Amazon, and the
mail search is the convenience. Do not let a quiet mail search stand as evidence
that nothing was bought.

PRICE: $6.49 per unit, qty 2, read from the order-details page, which is the
only sanctioned Amazon source. Item line $6.49, Item(s) Subtotal $12.98,
Shipping & Handling $0.00, Estimated tax $0.00, Grand Total $12.98. Nothing is
masked here — no rewards points, no gift card, no Subscribe & Save line — so
for once the email total and the line agree. The line is still what was used;
the rule is not "check whether the total happens to match", it is "read the
line", because agreement is not observable from the email alone.

QTY 2 IS TWO CORDS, NOT A PACK OF TWO. The "x 2" in the vendor title is the
number of RECEPTACLES on one cord — a single NEMA 5-15P plug feeding two
5-15R outlets. One purchased unit is one Y-cord. So pack_quantity stays at 1
and the line carries quantity=2. Getting this backwards would have booked one
cord at $12.98 with a pack of 2, which reads identically on the PO total and
wrongly everywhere else.

CATEGORY Electrical, following #1051 Leviton 5821 Receptacle NEMA 6-20R — the
only NEMA-connector precedent on the instance and the same kind of object, a
mains AC connector body. NOT Shop/Accessories, where the two Tormach cords
(#594, #596) live: those are there because they are machine accessories that
arrived on a machine bundle, not because a power cord belongs under Shop.

default_location left EMPTY on purpose — nobody has told this job where mains
cordage lives, and default_location means where a SPARE goes home. The receive
step takes an explicit --to. Not a decision-queue item; it resolves itself when
someone checks the box in.

Searched before creating, across name/description/IPN/keywords/supplier SKU
(Cablelera, "power cord", splitter, "NEMA 5-15", ZWACPQAG, B00FRODUR4,
"extension cord", "Y adapter", outlet, 5-15R, "power strip", IEC): 34 hits,
none of them this. The only near misses are #594 Cord Power 115VAC 6ft (a plain
Tormach cord, no splitter), #596 Tormach Power Strip 3 AC Kit, and #269
PowerCube Extended USB — a 4-outlet strip with USB, and separately worth noting
that #269 is sitting in the "Fuses" category, which is wrong but is NOT this
run's business to move. New part.

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
ARRIVES = date(2026, 9, 10)

ORDERS = [
    dict(
        ref="113-7332958-8875426",
        asin="B00FRODUR4",
        price="6.49",
        qty="2",
        pack="1",
        category="Electrical",
        name="Power Cord Splitter, NEMA 5-15P to 2x 5-15R, 16AWG 13A 125V",
        description=("orig: Cablelera Power Cord Extension and Splitter, NEMA "
                     "5-15P to NEMA 5-15R x 2, 16 AWG, 13A, 125V "
                     "(ZWACPQAG-14) Black"),
        # Part.keywords is capped at 250 characters and Part.save() calls
        # full_clean(), so an over-long list is a hard ValidationError.
        keywords=("power cord, splitter, Y cord, Y adapter, two outlet, "
                  "NEMA 5-15P, NEMA 5-15R, 5-15, 15A plug, 13A, 125V, 120V, "
                  "16 AWG, SJT, mains, AC, extension, pigtail, one to two, "
                  "duplex, Cablelera, ZWACPQAG-14, bench power"),
        sold_by="Amazon.com",
        price_note=(
            "$6.49 EACH, qty 2, read from the order-details page — item line "
            "$6.49, Item(s) Subtotal $12.98, Shipping & Handling $0.00, "
            "Estimated tax $0.00, Grand Total $12.98.\n\n"
            "Nothing is masked on this order: no rewards points, no gift card, "
            "no Subscribe & Save line, so the Grand Total happens to equal the "
            "line total. The line was still the source. The standing rule is "
            "not 'use the total when it matches' — whether it matches is not "
            "visible from the email, which is the entire reason the rule says "
            "read the order page."
        ),
        notes=(
            "QTY 2 IS TWO CORDS. pack_quantity is 1 and the line quantity is 2.\n\n"
            "The 'x 2' in the vendor title counts RECEPTACLES, not units in a "
            "bag: one NEMA 5-15P plug feeds two NEMA 5-15R outlets on a single "
            "Y-cord. Two of those cords were bought. Reading the title's 'x 2' "
            "as a pack would have created one part at $12.98 with pack=2 — the "
            "PO total is identical either way, which is exactly why this is "
            "worth stating: the error would not have shown up anywhere it was "
            "cheap to catch.\n\n"
            "WHAT IT IS. Moulded mains splitter cord, 16 AWG, rated 13 A at "
            "125 V. The 13 A rating is the CORD's, and it is the limit for "
            "BOTH outlets ADDED TOGETHER — a splitter divides one 15 A branch, "
            "it does not create a second one. Two loads that each draw 10 A "
            "will overload this cord long before the breaker notices, because "
            "the breaker is protecting 14 AWG house wiring and this is a "
            "shorter, thinner, moulded run. Do not feed two heaters, two "
            "kettles, or a machine plus a shop vac from one of these.\n\n"
            "Length is NOT recorded because the vendor title does not state it "
            "and no other sanctioned source was read. Measure it at the bench "
            "when it lands rather than taking a figure off a product page — "
            "this instance has been burned by constructed Amazon URLs before, "
            "and a wrong length here would be a fact nobody re-checks.\n\n"
            "default_location deliberately EMPTY — nobody has said where mains "
            "cordage lives, and default_location means where a SPARE goes "
            "home. Receiving takes an explicit --to.\n\n"
            "CATEGORY Electrical, following #1051 Leviton 5821 Receptacle NEMA "
            "6-20R, the only NEMA-connector precedent and the same kind of "
            "object. Not Shop/Accessories: the two Tormach cords there (#594, "
            "#596) are filed as machine-bundle accessories, which is a "
            "provenance, not a taxonomy for cordage.\n\n"
            "Searched before creating across name/description/IPN/keywords/SKU "
            "(Cablelera, power cord, splitter, NEMA 5-15, ZWACPQAG, "
            "B00FRODUR4, extension cord, Y adapter, outlet, 5-15R, power "
            "strip, IEC): 34 hits, none of them this. Nearest are #594 a plain "
            "6 ft Tormach cord, #596 the Tormach 3 AC power strip kit, and "
            "#269 PowerCube Extended USB, a 4-outlet strip. New part."
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
