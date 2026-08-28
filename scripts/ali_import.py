"""Create PurchaseOrders for AliExpress orders under Company #10.

Scott's ruling 2026-08-28: "1 keep under aliexpress" / "one PO per order number
under Company #10". AliExpress splits one checkout into one order per seller, so
the order number - not the checkout - is the PO grain and the idempotency key.

Prices are taken from the ITEM LINE on the order-details page, never from the
order Total: Total includes shipping, which on cheap AliExpress items routinely
exceeds the item (see aliexpress-price-rule-RETRACTED). Measured today, this is
not hypothetical - order 8213410090395753 reads $2.69 x2 on the line, subtotal
$5.38, total $7.37, so the queue's "DERIVED $3.685 = 7.37/2" was 37% high.

SupplierParts are REUSED where an exact product+variant match already exists and
created only where none does. AliExpress SKUs in this instance are order-line
strings ("<orderid>/<variant>"), a known defect; this script does not spread it
further than the one new SupplierPart it must create.

Every write is re-read and asserted - this install has a documented silent-save
trap where .save() reports success and writes nothing.

--commit to write; default is a dry run.
"""
import os
import sys
import django
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.db import transaction                          # noqa: E402
from company.models import Company, SupplierPart           # noqa: E402
from order.models import PurchaseOrder                     # noqa: E402
from order.status_codes import PurchaseOrderStatus         # noqa: E402
from part.models import Part                               # noqa: E402

COMMIT = "--commit" in sys.argv

ALI = Company.objects.get(pk=10)

# Everything below is verbatim from the AliExpress order-details page, read
# 2026-08-28 with Scott's session live. seller/title/variant/unit/qty/dates.
ORDERS = [
    dict(
        order="8213410090415753",
        seller="Shenzhen Hi-Link Electronic Module Store",
        placed=date(2026, 8, 23), eta=date(2026, 9, 9),
        part_pk=491,
        sku="8211821285145753/5 PCS HLK-5M05B",   # existing exact-variant match
        title=("Hi-Link 5W 5V 1A Low Cost Solution HLK-5M05B 5M03B HLK-5M09B "
               "HLK-5M12B HLK-5M15B HLK-5M24B AC DC Intelligent Power Supply Module"),
        variant="5 PCS HLK-5M05B",
        unit=Decimal("16.96"), qty=Decimal("1"),
        subtotal=Decimal("16.96"), total=Decimal("16.96"),
        retires=156,
    ),
    dict(
        order="8213410090395753",
        seller="LUOMEI Store",
        placed=date(2026, 8, 23), eta=date(2026, 9, 3),
        part_pk=490,
        sku="8211821285125753/15MH 4A 0.6 Wire",  # existing exact-variant match
        title=("5MH 10MH 15MH 4A Annular Common Mode Filter Inductor 0.6 Wire "
               "Choke Ring Inductance 14*9*5mm 2MH 5A 0.7 Wire"),
        variant="15MH 4A 0.6 Wire",
        unit=Decimal("2.69"), qty=Decimal("2"),
        subtotal=Decimal("5.38"), total=Decimal("7.37"),
        retires=157,
    ),
    dict(
        order="8214467898875753",
        seller="Ali-TG820 Home Goods Store",
        placed=date(2026, 8, 28), eta=date(2026, 9, 10),
        part_pk=418,
        sku="8214467898875753/TG820 GC9A01 1.28in round",   # created below
        title=("[TG820]TFT Display 1.28 Inch TFT LCD Display Module Round RGB "
               "240*240 GC9A01 Driver 4 Wire SPI Interface 240x240 PCB For Arduino"),
        variant=None,
        unit=Decimal("5.01"), qty=Decimal("6"),
        subtotal=Decimal("30.06"), total=Decimal("30.06"),
        retires=None,
    ),
    dict(
        order="8214467898895753",
        seller="Advanced Tech",
        placed=date(2026, 8, 28), eta=date(2026, 9, 10),
        part_pk=418,
        sku="8214467898875753/TG820 GC9A01 1.28in round",   # same SupplierPart
        title=("TFT Display 1.28 Inch TFT LCD Display Module Round RGB 240*240 "
               "GC9A01 Driver 4 Wire SPI Interface 240x240 PCB For Arduino"),
        variant="1PCS",
        unit=Decimal("0.99"), qty=Decimal("1"),
        subtotal=Decimal("0.99"), total=Decimal("0.99"),
        retires=None,
    ),
]

NEW_SKU = "8214467898875753/TG820 GC9A01 1.28in round"


def ensure_supplier_part():
    """Part 418's existing AliExpress SupplierParts are a different listing
    (order 8203108944..., variants 'Circular plate' / 'Module no Touch'), so
    neither can be claimed as this product without guessing. One new one covers
    both of today's orders; the differing prices live on the PO lines, which is
    where price belongs."""
    sp = SupplierPart.objects.filter(supplier=ALI, SKU=NEW_SKU).first()
    if sp:
        print(f"  supplier part exists: pk={sp.pk}")
        return sp
    if not COMMIT:
        print(f"  DRY RUN would create SupplierPart {NEW_SKU!r} on part 418")
        return None
    sp = SupplierPart.objects.create(
        part=Part.objects.get(pk=418), supplier=ALI, SKU=NEW_SKU,
        description=("1.28in round GC9A01 240x240 IPS SPI TFT. Bought 2026-08-28 "
                     "from two AliExpress sellers at once: Ali-TG820 Home Goods "
                     "Store ($5.01 x6) and Advanced Tech ($0.99 x1). SKU is an "
                     "order-line string, the house AliExpress form."),
    )
    sp.refresh_from_db()
    assert sp.pk and sp.SKU == NEW_SKU, "supplier part write did not stick"
    print(f"  CREATED SupplierPart pk={sp.pk} {sp.SKU!r}")
    return sp


def main():
    print(f"{'COMMIT' if COMMIT else 'DRY RUN'} - AliExpress import, "
          f"{len(ORDERS)} order(s)\n")

    print("SupplierPart for part 418:")
    ensure_supplier_part()
    print()

    created = []
    for o in ORDERS:
        ref = o["order"]
        existing = PurchaseOrder.objects.filter(supplier_reference=ref).first()
        if existing:
            print(f"SKIP {ref}: already {existing.reference}")
            continue

        sp = SupplierPart.objects.filter(supplier=ALI, SKU=o["sku"]).first()
        if sp is None:
            print(f"SKIP {ref}: no SupplierPart {o['sku']!r} (dry run?)")
            continue

        shipping = o["total"] - o["subtotal"]
        note = (f"AliExpress order {ref}. Seller: {o['seller']}. "
                f"Item price {o['unit']} x{o['qty']} read verbatim from the "
                f"order-details page 2026-08-28. Subtotal {o['subtotal']}, "
                f"order total {o['total']}"
                + (f" (includes {shipping} shipping, NOT on the line)."
                   if shipping else " (no shipping added)."))

        if not COMMIT:
            print(f"WOULD CREATE  {ref}  part {o['part_pk']}  "
                  f"{o['unit']} x{o['qty']}  eta {o['eta']}")
            continue

        with transaction.atomic():
            po = PurchaseOrder.objects.create(
                reference=PurchaseOrder.generate_reference(),
                supplier=ALI,
                supplier_reference=ref,
                description=f"AliExpress {ref} - {o['seller']}"[:250],
                target_date=o["eta"],
                issue_date=o["placed"],
                notes=note,
            )
            line = po.lines.create(
                part=sp,
                quantity=o["qty"],
                purchase_price=o["unit"],
                purchase_price_currency="USD",
                notes=(f"{o['title']}"
                       + (f" | variant: {o['variant']}" if o["variant"] else "")),
            )
            po.status = PurchaseOrderStatus.PLACED.value
            po.save()

        po.refresh_from_db()
        line.refresh_from_db()
        assert po.supplier_reference == ref, "supplier_reference did not stick"
        assert po.status == PurchaseOrderStatus.PLACED.value, "status did not stick"
        assert line.quantity == o["qty"], "quantity did not stick"
        assert Decimal(str(line.purchase_price.amount)) == o["unit"], \
            "price did not stick"
        print(f"CREATED {po.reference}  supplier_ref={ref}  "
              f"{line.quantity} x {line.purchase_price}  "
              f"status={po.get_status_display()}  target={po.target_date}")
        created.append((po, o))

    # The placeholder shopping list TO-ORDER-ALI (pk 60) is what these two
    # orders FULFIL. Leaving its lines unmarked is how the shortfall gets
    # ordered a second time - the risk PO-0019 was cancelled over.
    if COMMIT and created:
        placeholder = PurchaseOrder.objects.get(pk=60)
        for po, o in created:
            if not o["retires"]:
                continue
            ln = placeholder.lines.filter(pk=o["retires"]).first()
            if ln is None or "FULFILLED" in (ln.notes or ""):
                continue
            ln.notes = ((ln.notes or "") +
                        f" || FULFILLED 2026-08-28 by {po.reference} "
                        f"(AliExpress order {o['order']}, {o['qty']} @ {o['unit']}). "
                        f"Do not re-order from this line.")
            ln.save()
            ln.refresh_from_db()
            assert "FULFILLED" in ln.notes, "placeholder note did not stick"
            print(f"  marked TO-ORDER-ALI line {ln.pk} FULFILLED by {po.reference}")

    print(f"\n{'created' if COMMIT else 'would create'} {len(created) if COMMIT else ''} PO(s)")


main()
