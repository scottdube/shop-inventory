"""Queue C for the 2026-08-27 22:40 daytime sweep — one Amazon PO.

Order 113-8690960-8633066, placed 2026-08-27, `absent` from po_check before
this ran. The other three orders in the window were already handled:

  112-5876133-0975416  Bounty paper towels — SKIPPED, sitting on the decision
                       queue as household-consumables-in-or-out awaiting a
                       ruling. Not re-journalled as a fresh contradiction.
  111-8717191-1899411  -> PO-0143 (created by the 08-26 13:15 sweep)
  111-4846191-6220252  -> PO-0144 (same)
  113-1545085-3620205  CANCELLED by Amazon — nothing was bought, no PO.

PRICE. Another textbook case of the rewards/gift-card trap, so it is worth
recording: the order-details page reads

    Item(s) Subtotal: $49.99   Shipping & Handling: $0.00
    Total before tax: $49.99   Estimated tax: $0.00
    Gift Card Amount: -$39.45  Grand Total: $10.54

$49.99 is the price. $10.54 is what the card was charged after a gift-card
balance was applied invisibly, and booking it would have understated this
item by 79%% with nothing downstream able to detect it.

PACK QUANTITY, and why the line is qty 1 and not qty 2. The kit is two
identical 450 mm rails with four HGH15CA blocks. Splitting $49.99 across two
rails ($24.995) would be a DERIVED price, and it is not necessary here: "a
pack is a supplier fact, not a part" — the pack count is stated verbatim in
the vendor title ("2pcs 450mm"), so it goes on the SupplierPart as
pack_quantity=2 and the line carries the one price that actually appears on
the order. This is the opposite call from the Chip Quik line on 08-26, and
deliberately so: there "32ft. In 6" was a guess about what the words meant,
here "2pcs" is a count.

**Receiving this line will need a human to look.** receive_line_item()
ignores pack_quantity and books the whole pack price against one piece, so
whoever checks this in gets 2 rails at $49.99 each unless they intervene.
Said in the PO notes as well as here.

PART IDENTITY. part_find returns 0 hits for HGR15 and 0 for HGH15; the only
linear rail in the catalogue is #1117 "Linear Rail MGN9, 200 mm, with
carriage", a different and much smaller profile. So this is new, and #1117 is
the naming precedent — rail profile, length, and its carriage in one part
name, because that is the unit that goes on a machine.

default_location is left NULL on purpose. #1117's home is sized for a 200 mm
MGN9; a 450 mm HGR15 rail is a different physical object and guessing a home
for it would put a spare somewhere it does not fit. A human placing it on
receipt is one decision; a wrong default_location is silent forever.
"""
import os
import sys
from datetime import date
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
TEMPLATE = Part.objects.get(pk=1117)          # Linear Rail MGN9 — category only
CATEGORY = TEMPLATE.category

ASIN = "B0FH9XGQZP"
REF = "113-8690960-8633066"

SPEC = dict(
    name="Linear Rail HGR15, 450 mm, with 2 HGH15CA carriages",
    description=("orig: HGR15 450mm Linear Guide kit,2pcs 450mm hgr15 Linear Rail "
                 "with 4pcs HGH15CA Carriage Block and HG15 end Stop Block"),
    keywords=("linear rail, linear guide, HGR15, HG15, HGH15CA, carriage block, "
              "profile rail, 15 mm, 450 mm, recirculating ball, CNC motion, "
              "linear motion"),
)

NOTES = (
    f"Amazon order {REF}, placed 2026-08-27, arriving Monday 2026-08-31.\n"
    "Sold by ZHBRING.\n\n"
    "PRICE $49.99 read from the order-details page, NOT from the email. The "
    "page's Grand Total is $10.54 because a $39.45 gift-card balance was "
    "applied; the item price is $49.99 and that is what is booked.\n\n"
    "PACK: the kit is 2 identical 450 mm rails + 4 HGH15CA blocks. "
    "pack_quantity=2 is on the SupplierPart and the line is qty 1 at the "
    "$49.99 that appears on the order — no derived per-rail price.\n\n"
    "*** ON RECEIVING, LOOK AT THIS LINE. *** receive_line_item() ignores "
    "pack_quantity and books the full pack price against a single piece. "
    "Checking this in without intervening yields 2 rails at $49.99 each "
    "instead of 2 at $24.995. Check qty x price against the line total."
)

base = get_base_url() or "http://192.168.50.10:8001"

if PurchaseOrder.objects.filter(supplier_reference=REF).exists():
    print("ALREADY EXISTS — skipping (idempotency key is supplier_reference)")
    raise SystemExit(0)

sp = SupplierPart.objects.filter(supplier=AMAZON, SKU=ASIN).first()
if sp:
    print(f"reuse  SupplierPart {sp.pk}  {ASIN} -> part {sp.part_id} {sp.part.name}")
else:
    for field, value in (("name", SPEC["name"]), ("IPN", ASIN)):
        dupe = Part.objects.filter(**{field: value}).first()
        if dupe:
            raise SystemExit(f"refusing to create: part with {field}={value!r} exists (#{dupe.pk})")

    p = Part.objects.create(
        name=SPEC["name"],
        description=SPEC["description"],
        keywords=SPEC["keywords"],
        IPN=ASIN,
        category=CATEGORY,
        default_location=None,
        component=True,
        purchaseable=True,
        active=True,
    )
    check = Part.objects.get(pk=p.pk)          # silent-save trap: re-read
    assert check.name == SPEC["name"] and check.IPN == ASIN, f"part {p.pk} did not stick"
    print(f"CREATE part {check.pk}: {check.name}  cat={check.category}")

    sp = SupplierPart.objects.create(supplier=AMAZON, part=p, SKU=ASIN, pack_quantity="2")
    fresh = SupplierPart.objects.get(pk=sp.pk)
    assert fresh.SKU == ASIN, f"supplierpart {sp.pk} did not stick"
    print(f"CREATE SupplierPart {fresh.pk}: {ASIN} pack_quantity={fresh.pack_quantity}")

po = PurchaseOrder.objects.create(
    reference=PurchaseOrder.generate_reference(),
    supplier=AMAZON,
    supplier_reference=REF,
    description=f"Amazon order {REF}",
    notes=NOTES,
    issue_date=date(2026, 8, 27),
    target_date=date(2026, 8, 31),
)
po.status = PurchaseOrderStatus.PLACED.value
po.save()

po = PurchaseOrder.objects.get(pk=po.pk)
assert po.supplier_reference == REF, "PO supplier_reference did not stick"
assert po.issue_date == date(2026, 8, 27), "PO issue_date did not stick"
assert po.target_date == date(2026, 8, 31), "PO target_date did not stick"
assert po.status == PurchaseOrderStatus.PLACED.value, f"PO status is {po.status}, not PLACED"
print(f"CREATE {po.reference}  status=PLACED  supplier_reference={po.supplier_reference}")

li = PurchaseOrderLineItem.objects.create(
    order=po, part=sp, quantity=Decimal("1"), purchase_price=Decimal("49.99"),
)
li = PurchaseOrderLineItem.objects.get(pk=li.pk)
assert li.purchase_price.amount == Decimal("49.99"), f"line {li.pk} price did not stick"
print(f"LINE {li.pk}: {sp.part.name[:60]} qty={li.quantity} unit={li.purchase_price}")
print(f"{base}/order/purchase-order/{po.pk}/")
