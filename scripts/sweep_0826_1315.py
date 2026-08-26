"""Queue C for the 2026-08-26 13:15 daytime sweep — two Amazon POs.

Orders (both placed 2026-08-26, both `absent` from po_check before this ran):

  111-8717191-1899411  Chip Quik SMDSWLTLFP32 low-temp lead-free solder wire
  111-4846191-6220252  desoldering nozzles N61-10 (1.6mm) and N61-06 (1.3mm)

Prices come from amazon.com/gp/your-account/order-details, NOT from the email.
Order 111-8717191-1899411 is the canonical illustration of why: its `Grand
Total:` is **$0.00** because $57.46 of rewards points were applied invisibly.
The item is a $57.46 item. Booking $0.00 would have written a lie into the
cost history that nothing downstream could ever detect.

Part identity, decided from dupe_probe_0826 / dupe_detail_0826:

  * N61-06 1.3mm ALREADY EXISTS as part 213 (IPN/ASIN B07DMWBRB9, SupplierPart
    113). Parts 86 and 214 look like duplicates in a name search but are
    tombstones -- their descriptions read "MERGED into part #213 / #87". So no
    new part, and no merge decision to raise.
  * N61-10 1.6mm does not exist -> created.
  * Chip Quik SMDSWLTLFP32 does not exist -> created.

Two naming calls worth stating, because both are cases of NOT writing down
something that would have looked tidier:

  * The N61-10 listing (sold by "Vigent") never claims the Hakko brand, unlike
    the N61-06 and N61-07 listings. So the canonical name omits "Hakko" rather
    than inheriting it from its shelf-mates. N61-10 is the nozzle designation;
    the maker is not established by anything measured here.
  * The vendor title "(32ft. In 6)" probably means six tubes, but "probably" is
    not a supplier fact. pack_quantity stays 1, which books the whole $57.46
    against one piece -- conservative, and it cannot produce the inverted error
    that read 19 bins as $208.62 each. Flagged in the PO notes instead.

Leaves both POs in PLACED. Receiving is a human checking the box in.
Every write is re-read before it is reported, per the silent-save trap.
"""
import os
import sys
from decimal import Decimal

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402
from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402
from InvenTree.helpers_model import get_base_url  # noqa: E402

AMAZON = Company.objects.get(pk=9)
TEMPLATE = Part.objects.get(pk=213)          # canonical N61-06, for category/units
CATEGORY = TEMPLATE.category
HOME = TEMPLATE.default_location              # A3-R1C2, the FR-301 nozzle drawer

NEW_PARTS = {
    "B0H6W5GRPB": dict(
        name="Desoldering Nozzle 1.6mm N61-10 (FR-301/FR-4101)",
        description="orig: N61-10 Desoldering Nozzle 1.6mm Tip for FR-301 FR-410",
        keywords=("desoldering nozzle, n61-10, N61, 1.6mm, FR-301, FR-4101, "
                  "desolder tip, solder sucker nozzle, vacuum desolder"),
        location=HOME,
    ),
    "B071V83B5G": dict(
        name="Chip Quik SMDSWLTLFP32 Low-Temp Lead-Free Solder Wire (32 ft)",
        description="orig: Chip Quik SMDSWLTLFP32 Solder Wire Lead-Free Low Temp (32ft. In 6)",
        keywords=("solder wire, chip quik, chipquik, SMDSWLTLFP32, low temperature solder, "
                  "low temp, lead-free, lead free solder, SMD rework, bismuth"),
        location=None,
    ),
}

ORDERS = [
    dict(
        ref="111-8717191-1899411",
        notes=("Amazon order 111-8717191-1899411, placed 2026-08-26.\n"
               "Prices read from the order-details page. The confirmation email's "
               "Grand Total reads $0.00 -- $57.46 of rewards points were applied. "
               "The item price is $57.46 and that is what is booked.\n"
               "pack_quantity=1: the vendor title says '32ft. In 6', which probably "
               "means six tubes, but that is not confirmed, so the line is booked as "
               "one piece at the full line price rather than guessing a divisor."),
        lines=[("B071V83B5G", Decimal("1"), Decimal("57.46"))],
    ),
    dict(
        ref="111-4846191-6220252",
        notes=("Amazon order 111-4846191-6220252, placed 2026-08-26.\n"
               "Per-item prices read from the order-details page: N61-10 $15.89 "
               "(sold by Vigent), N61-06 $16.55 (sold by TM-Horsehill). These sum to "
               "$32.44 against an order-history total of $31.65; the $0.79 difference "
               "is not explained on the page, and the per-item figures are used "
               "because they are the ones stated verbatim per line."),
        lines=[("B0H6W5GRPB", Decimal("1"), Decimal("15.89")),
               ("B07DMWBRB9", Decimal("1"), Decimal("16.55"))],
    ),
]


def supplier_part_for(asin):
    """Return the Amazon SupplierPart for an ASIN, creating part+SKU if new."""
    sp = SupplierPart.objects.filter(supplier=AMAZON, SKU=asin).first()
    if sp:
        print(f"  reuse  SupplierPart {sp.pk}  {asin} -> part {sp.part_id} {sp.part.name}")
        return sp

    spec = NEW_PARTS[asin]
    dupe = Part.objects.filter(name=spec["name"]).first()
    if dupe:
        raise SystemExit(f"refusing to create: part named {spec['name']!r} already exists (#{dupe.pk})")

    p = Part.objects.create(
        name=spec["name"],
        description=spec["description"],
        keywords=spec["keywords"],
        IPN=asin,
        category=CATEGORY,
        default_location=spec["location"],
        component=True,
        purchaseable=True,
        active=True,
    )
    check = Part.objects.get(pk=p.pk)          # silent-save trap: re-read, do not trust
    assert check.name == spec["name"] and check.IPN == asin, f"part {p.pk} did not stick"
    print(f"  CREATE part {p.pk}: {check.name}")

    sp = SupplierPart.objects.create(supplier=AMAZON, part=p, SKU=asin, pack_quantity="1")
    assert SupplierPart.objects.get(pk=sp.pk).SKU == asin, f"supplierpart {sp.pk} did not stick"
    print(f"  CREATE SupplierPart {sp.pk}: {asin}")
    return sp


base = get_base_url() or "http://192.168.50.10:8001"

for order in ORDERS:
    print(f"\n=== {order['ref']}")
    if PurchaseOrder.objects.filter(supplier_reference=order["ref"]).exists():
        print("  ALREADY EXISTS — skipping (idempotency key is supplier_reference)")
        continue

    # generate_reference() only. A raw Amazon number here clamps reference_int
    # to int32 max and permanently breaks reference generation instance-wide.
    po = PurchaseOrder.objects.create(
        reference=PurchaseOrder.generate_reference(),
        supplier=AMAZON,
        supplier_reference=order["ref"],
        description=f"Amazon order {order['ref']}",
        notes=order["notes"],
    )
    po.status = PurchaseOrderStatus.PLACED.value
    po.save()

    po = PurchaseOrder.objects.get(pk=po.pk)
    assert po.supplier_reference == order["ref"], "PO supplier_reference did not stick"
    assert po.status == PurchaseOrderStatus.PLACED.value, f"PO status is {po.status}, not PLACED"
    print(f"  CREATE {po.reference}  status=PLACED  supplier_reference={po.supplier_reference}")

    for asin, qty, unit in order["lines"]:
        sp = supplier_part_for(asin)
        li = PurchaseOrderLineItem.objects.create(
            order=po, part=sp, quantity=qty, purchase_price=unit,
        )
        li = PurchaseOrderLineItem.objects.get(pk=li.pk)
        assert li.purchase_price.amount == unit, f"line {li.pk} price did not stick"
        print(f"  LINE {li.pk}: {sp.part.name[:60]} qty={li.quantity} unit={li.purchase_price}")

    print(f"  {base}/order/purchase-order/{po.pk}/")
