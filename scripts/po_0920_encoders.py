"""Queue C: Amazon order 113-6751453-2901036 (2026-09-20) -> PO only, NO new part.

Taiss 5PCS Rotary Encoder Switch Push Button EC11 360 Degree 5 Pins 20 Detents
Points Digital Potentiometer with Knob Cap. ASIN B07F24TRYG, sold by the
marketplace seller "SEA-GULL". One pack, arriving 2026-09-21.

NO PART IS CREATED. The duplicate scan found part #200 already carrying
IPN=B07F24TRYG and an Amazon SupplierPart with SKU B07F24TRYG, and the ASIN was
read off the order-details page itself (the product anchor resolves to
/dp/B07F24TRYG), not inferred from the title. Identity is therefore established
on the field mark, not on a borrowed catalogue number.

PRICE SOURCE -- the order-details page, per item:

    Taiss 5PCS Rotary Encoder Switch ... with Knob Cap    9.99 x 1
                                                          ----
                                                          9.99

**Booked at $9.99. The email and the order list both say Grand Total $2.63.**
The page reads Item(s) Subtotal $9.99, shipping $0.00, tax $0.00, Gift Card
-$7.36, Grand Total $2.63. A gift-card balance is a payment instrument, not a
discount -- same shape as PO-0175 (nanoHD), decided there and not re-litigated.
Booking $2.63 would have understated the pack by 74%.

PACK IS REPORTED, NEVER WRITTEN. The listing title says 5PCS. If the existing
SupplierPart still reads pack 1, that is the recurring multipack bug and it is
the SAME QUESTION as the open `zip-bag-pack-quantity-400-vs-1` decision item --
a costing call that moves price-per-piece on every future receive, not a
transcription. This script prints what it found and changes nothing; the sweep
riders it onto that open item instead of opening a third copy of the question.

PLACED, never received. A human checks it in.
"""
import argparse
import datetime
import os
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402
from part.models import Part  # noqa: E402

ORDER = "113-6751453-2901036"
ISSUE = datetime.date(2026, 9, 20)
ARRIVES = datetime.date(2026, 9, 21)
SUBTOTAL = 9.99

ASIN = "B07F24TRYG"
UNIT = "9.99"
QTY = 1

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

# ---------------------------------------------------------------- idempotency
dup_po = PurchaseOrder.objects.filter(
    Q(supplier_reference=ORDER) | Q(reference=ORDER))
if dup_po.exists():
    sys.exit(f"!! PO already exists for {ORDER}: "
             f"{[p.reference for p in dup_po]} — nothing to do")

# ------------------------------------------------- resolve the EXISTING part
sp = SupplierPart.objects.filter(supplier=amazon, SKU=ASIN).first()
if sp is None:
    sys.exit(f"!! no Amazon supplier part for {ASIN} — this script assumes the "
             f"part already exists; re-check before creating anything")
part = sp.part
print(f"USING existing part #{part.pk} {part.name}")
print(f"  cat={part.category.pathstring if part.category else None}  "
      f"IPN={part.IPN}  active={part.active}  stock={part.total_stock}")
print(f"  sp #{sp.pk} SKU={sp.SKU} pack_quantity={sp.pack_quantity} "
      f"pack_quantity_native={sp.pack_quantity_native}")

# Pack is REPORTED, not written -- see the module docstring.
if float(sp.pack_quantity_native) == 1:
    print("  !! PACK LOOKS WRONG: listing title says 5PCS, supplier part says 1."
          "\n     NOT CHANGED — costing call, rider to zip-bag-pack-quantity-400-vs-1.")

# ------------------------------------------- duplicate scan (report, no write)
dupes = (Part.objects.filter(name__icontains="EC11")
         | Part.objects.filter(IPN=ASIN)
         | Part.objects.filter(description__icontains=ASIN)
         | Part.objects.filter(description__icontains="EC11")).distinct()
print("\nduplicate scan (EC11 / ASIN):")
for d in dupes:
    print(f"  #{d.pk} active={d.active} stock={d.total_stock} "
          f"cat={d.category.pathstring if d.category else None}  {d.name}")

total = float(UNIT) * QTY
print(f"\nreconcile: lines sum {total:.2f} vs page subtotal {SUBTOTAL:.2f}")
assert abs(total - SUBTOTAL) < 0.005, "line price does not reconcile — refusing"

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ---------------------------------------------------------------- PO
po = PurchaseOrder(
    supplier=amazon,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=f"Amazon order {ORDER} — EC11 rotary encoders (5-pack)",
    issue_date=ISSUE,
    target_date=ARRIVES,
    status=PurchaseOrderStatus.PLACED.value,
    notes=("Auto-created by the queue C daytime sweep, 12:40 run 2026-09-20.\n\n"
           "PRICE SOURCE: the order-details page, per item — $9.99.\n\n"
           "THE GRAND TOTAL ON THIS ORDER IS $2.63 AND IS NOT THE PRICE. The "
           "page reads Item(s) Subtotal $9.99, shipping $0.00, tax $0.00, Gift "
           "Card -$7.36, Grand Total $2.63. A gift-card balance is a payment "
           "instrument, not a discount — the encoders are a $9.99 asset that "
           "cost $2.63 out of pocket. Same shape as PO-0175 (nanoHD), decided "
           "there.\n\n"
           "NO NEW PART. Part #200 already carries IPN B07F24TRYG and the "
           "matching Amazon supplier part; the ASIN was read off the product "
           "anchor on the order-details page, not inferred from the title.\n\n"
           "Sold by the marketplace seller \"SEA-GULL\", not by Amazon "
           "directly; the supplier is Amazon as the marketplace, per the "
           "convention used by every other marketplace PO here.\n\n"
           "PLACED, not received. Arriving 2026-09-21; receive with "
           "receive_po.py when the box is physically checked in."),
)
po.save()
po.refresh_from_db()
assert po.status == PurchaseOrderStatus.PLACED.value, "PO status did not stick"
assert po.supplier_reference == ORDER, "supplier_reference did not stick"
assert po.reference != ORDER, "vendor number leaked into reference"
print(f"\nCREATED {po.reference} supplier_ref={po.supplier_reference}")

li = PurchaseOrderLineItem(
    order=po, part=sp, quantity=QTY,
    purchase_price=UNIT, purchase_price_currency="USD",
    notes=("Per-item price from the Amazon order-details page: one 5-piece "
           "pack at $9.99. The Grand Total is $2.63 because a $7.36 gift-card "
           "balance paid the rest — payment method, not price."))
li.save()
li.refresh_from_db()
assert float(li.purchase_price.amount) == float(UNIT), \
    f"price did not stick: {li.purchase_price}"
print(f"    line: qty {li.quantity} @ {li.purchase_price}")

po.refresh_from_db()
booked = sum(float(l.purchase_price.amount) * float(l.quantity)
             for l in po.lines.all())
print(f"\nDONE  {po.reference}  lines={po.lines.count()}  booked=${booked:.2f}"
      f"  (page subtotal ${SUBTOTAL:.2f})")
assert abs(booked - SUBTOTAL) < 0.005, "booked total drifted from the page"
