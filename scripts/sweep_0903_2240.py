"""Queue C for the 2026-09-03 22:40 daytime sweep — one Amazon PO.

Window swept: last-po-sweep 2026-09-03 minus 1 day = from 2026-09-02.

WHAT WAS IN THE WINDOW AND WHY ONLY ONE PO. The known-vendor Gmail pass returned
twelve threads; eleven were not orders — six Amazon shipment notices, three
"Delay in shipping" notices, one review solicitation, and Amazon Pharmacy. A
second pass on `subject:"Ordered:"` (the confirmation subject Gmail's
`subject:order` does NOT match — whole-word matching, "Ordered" != "order",
the same trap the 09-02 08:40 sweep documented) found two confirmations, and
one batched po_check settled the whole set:

  113-0934611-9763450 -> PO-0157   111-4312729-1257045 -> PO-0155
  113-8466709-7941016 -> PO-0156   111-4901796-2449843 -> PO-0154
  8213410090415753    -> PO-0146   8213410090395753    -> PO-0147
  113-4088575-5438644 -> absent    <- the only new one, imported here

  Amazon Pharmacy (Mounjaro, delivered 09-02) — medical. Suppressed and NOT
                       transcribed, per the standing rule. Logged only as
                       "skipped (personal)".

The two AliExpress threads are "awaiting confirmation" delivery nags on orders
already imported 08-28, not new checkouts. Nothing to do.

PRICE $8.69, read from the order-details page, which is the only sanctioned
source for an Amazon price. Item(s) Subtotal $8.69 == the item line $8.69 ==
Grand Total $8.69, with $0.00 shipping and $0.00 tax, and NO rewards-points or
gift-card line. Clean. The check is not a formality — it caught a $3.86 points
deduction on the Solsop crimper two sweeps ago.

PACK QUANTITY = 5, and this one IS a real multipack, not an assortment. Five
identical PCF8574AP chips are five interchangeable pieces; contrast the DASBET
"11PCS" flaring kit imported 09-02, whose eleven pieces are the dies and yoke of
ONE tool and correctly got pack=1. So stock counts 5 pieces at $1.738 each, not
one unit at $8.69. Written through .save() (SupplierPart.objects.create calls
it), never a queryset .update() — per CLAUDE.md the pack is stored twice and
only `pack_quantity_native` is read at receive time; the assert below checks
BOTH fields actually landed, because five supplier parts were found in the
split state on 2026-09-03.

Deliberately NOT carrying forward the old RECEIVE_WARNING block that earlier
sweep scripts pasted into PO notes. It said receive_line_item() ignores the pack
and books the pack price against a single piece. That was corrected in CLAUDE.md
on 2026-09-03: receive_line_item multiplies by native and divides the price to
match, so a supplier part with a correct pack needs no hand repair at receipt.
Repeating a retracted warning in a PO note is how a retraction gets un-retracted.

CATEGORY Electronics/Interface (pk 135), matching #798 MCP2562-E/P CAN
Transceiver DIP-8 — the same shape of thing (a bare DIP interface chip) and the
most recent convention, created 2026-08-18. NOT the top-level `ICs` tree (pk 9):
those 22 parts are the 2026-08-15/16 bulk import and are mostly breakout MODULES
(relay boards, nRF24L01+ carriers, an SFP transceiver), not bare silicon. That
two IC trees coexist at all is a real structural ambiguity that will recur on
every IC this job imports, so it went on the decision queue rather than being
silently resolved a third different way here.

NO DUPLICATE. `part_find.py PCF8574 B0GF1Q1GNG "I/O expander" Bridgold` returned
2 hits, neither one this part: #15 is a Bridgold IRF4905 MOSFET (same seller,
different device) and #410 is a Diymore I2C LCD backpack MODULE. #410 is worth
noting rather than merging — that backpack is built AROUND a PCF8574, so it is
the same chip in a different form factor. A module is not its IC.
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
ISSUE = date(2026, 9, 3)
ARRIVES = date(2026, 9, 5)

ORDERS = [
    dict(
        ref="113-4088575-5438644",
        asin="B0GF1Q1GNG",
        price="8.69",
        pack="5",
        category="Electronics/Interface",
        name="PCF8574AP Remote 8-Bit I/O Expander for I2C, DIP-16",
        description=("orig: Bridgold 5pcs PCF8574AP Remote 8 Bit Input Output "
                     "Extender，2.5V to 6V."),
        # Part.keywords is capped at 250 characters and Part.save() calls
        # full_clean(), so an over-long list is a hard ValidationError, not a
        # truncation. This one was 277 on the first attempt.
        keywords=("PCF8574, PCF8574AP, I2C, IIC, TWI, I/O expander, IO expander, port "
                  "expander, GPIO expander, 8-bit, quasi-bidirectional, interrupt "
                  "output, open drain, DIP-16, through hole, address pins A0 A1 A2, "
                  "NXP, Bridgold, interface IC, LCD backpack chip"),
        sold_by="Bridgold Direct",
        price_note=(
            "$8.69 read from the order-details page, which is the only sanctioned "
            "source for an Amazon price. Item(s) Subtotal $8.69 == item line $8.69 "
            "== Grand Total $8.69; shipping $0.00, tax $0.00, and no rewards-points "
            "or gift-card line, so nothing is masked on this one. That is $1.738 per "
            "chip across the 5-pack — the line below is priced per PACK, and "
            "pack_quantity=5 is what turns it into a per-piece cost at receipt."
        ),
        notes=(
            "FIVE INTERCHANGEABLE CHIPS — pack_quantity=5 on purpose, and this is the "
            "multipack case, not the assortment case. Stock counts PIECES: receiving "
            "this line yields 5 pieces at $1.738 each, not 1 unit at $8.69. Contrast "
            "the DASBET \"11PCS\" flaring kit (PO-0157), where the eleven pieces are "
            "the dies and yoke of one tool and pack_quantity is correctly 1.\n\n"
            "WHAT IT IS. NXP/TI PCF8574AP: 8-bit quasi-bidirectional I/O expander on "
            "the I2C bus, DIP-16, 2.5-6V, with an open-drain INT output and three "
            "address pins (A0/A1/A2) giving 8 devices per bus. The 'AP' suffix is the "
            "address range 0x38-0x3F; the plain PCF8574 is 0x20-0x27. THAT DISTINCTION "
            "MATTERS and is the usual reason an expander does not answer a scan — if "
            "a sketch written for a PCF8574 finds nothing, check the address before "
            "suspecting the chip.\n\n"
            "RELATED, NOT A DUPLICATE:\n"
            "  #410  Diymore IIC/I2C/TWI/SPI Serial Interface Board Module\n"
            "That LCD backpack is built AROUND a PCF8574 — same silicon, different "
            "form factor. A module is not its IC, so the two stay separate; but "
            "whoever is debugging one may want the other on the bench.\n\n"
            "Searched before creating (PCF8574 / B0GF1Q1GNG / \"I/O expander\" / "
            "Bridgold, 2 hits, neither this part)."
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

        # .create() goes through save() -> clean(), which is what populates
        # pack_quantity_native. A queryset .update() would set only the text field
        # and leave the number that receiving actually reads at 1.
        sp = SupplierPart.objects.create(
            supplier=AMAZON, part=p, SKU=asin, pack_quantity=o["pack"],
        )
        fresh = SupplierPart.objects.get(pk=sp.pk)
        assert fresh.SKU == asin, f"supplierpart {sp.pk} did not stick"
        assert str(fresh.pack_quantity) == o["pack"], (
            f"supplierpart {sp.pk} pack_quantity={fresh.pack_quantity!r}, want {o['pack']!r}")
        assert Decimal(fresh.pack_quantity_native) == Decimal(o["pack"]), (
            f"supplierpart {sp.pk} pack_quantity_native={fresh.pack_quantity_native!r} "
            f"does not match pack_quantity={fresh.pack_quantity!r} — the split-field trap")
        print(f"CREATE SupplierPart {fresh.pk}: {asin} "
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
        order=po, part=sp, quantity=Decimal("1"), purchase_price=Decimal(o["price"]),
    )
    li = PurchaseOrderLineItem.objects.get(pk=li.pk)
    assert li.purchase_price.amount == Decimal(o["price"]), f"line {li.pk} price did not stick"
    print(f"LINE {li.pk}: {sp.part.name[:55]} qty={li.quantity} unit={li.purchase_price} "
          f"pack={sp.pack_quantity_native}")

    created.append((po.reference, ref, po.pk))

print("=" * 72)
for reference, ref, pk in created:
    print(f"{reference}  {ref}  {base}/order/purchase-order/{pk}/")
print(f"{len(created)} PO(s) created, all left in PLACED — nothing received, no stock made.")
