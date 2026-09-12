"""Queue C + A: Amazon order 113-0958514-9540223 (2026-09-11) -> PO + part + image.

One new order in tonight's window. Single line, so the per-item price is
readable without splitting anything:

    Item(s) Subtotal   $7.69
    Shipping & Handling $0.00
    Total before tax   $7.69
    Grand Total        $7.69

All four agree, which is what rules out a points/gift-card payment hiding
under the grand total. The price recorded here is the Item(s) Subtotal from
the order-details page -- the only sanctioned Amazon price source -- and NOT
the grand total, which is cash-after-payment-methods and must never become a
line price even on a single-item order.

Reference handling: the vendor order number goes in supplier_reference ONLY.
Putting a raw Amazon number in `reference` clamps reference_int at int32 max
and permanently breaks generate_reference(), so the reference is generated.

PLACED, never received: the box is not here (arriving 2026-09-13). A human
receives it with receive_po.py when it physically lands.

Queue A rides along because a part on an open PO jumps the image queue --
the hiRes URL was read out of the /dp/ page in a driven browser (the product
page is the defended surface, the m.media-amazon.com CDN is not) and the
bytes are verified by content, not by status code.
"""
import argparse
import datetime
import os
import sys
import urllib.request

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.core.files.base import ContentFile  # noqa: E402
from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402

ORDER = "113-0958514-9540223"
ASIN = "B09QD4S7BN"
ISSUE = datetime.date(2026, 9, 11)
UNIT = "7.69"
QTY = 1

NAME = "Cam Lock, 5/8 in, keyed alike, zinc alloy"
ORIG = ('Hecfu 1 Pack Cabinet Locks with Keys, 5/8" Cam Lock keyed Alike, Secure '
        "Drawer File Cabinet Mailbox Lock Replacement RV Storage Locks, Zinc Alloy")
DESC = ("Quarter-turn cabinet cam lock, 5/8 in barrel, zinc alloy body, supplied "
        "with keys. Keyed alike. Ships as a single lock. orig: " + ORIG)
KEYWORDS = ("cabinet lock, cam lock, camlock, drawer lock, quarter turn lock, "
            "keyed alike, file cabinet lock, locker lock, tool box lock, 5/8")
NOTES = (
    "Bought to replace a cabinet/drawer lock, Amazon order 113-0958514-9540223.\n\n"
    "KEYED ALIKE is the reason this listing and not another: every lock from this "
    "line opens on the same key, so a second one bought later still matches. If a "
    "replacement is ever needed, reorder this same ASIN rather than an equivalent "
    "-- an equivalent will be keyed differently and defeats the point.\n\n"
    "5/8 in is the BARREL LENGTH, which is what has to match the thickness of the "
    "door or drawer front it goes through; it is not the bore diameter. Measure the "
    "panel before assuming this one fits a different cabinet.\n\n"
    "NOT COUNTED. Ordered 2026-09-11, arriving 2026-09-13 -- no stock row exists "
    "and none should until the box is physically checked in."
)

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

dup_sp = SupplierPart.objects.filter(supplier=amazon, SKU=ASIN)
dup_part = Part.objects.filter(Q(name=NAME) | Q(description__icontains=ORIG[:40]))
print(f"idempotency: PO(s)={dup_po.count()} SupplierPart(s)={dup_sp.count()} "
      f"Part(s)={dup_part.count()}")
for p in dup_part:
    print(f"   existing part candidate: #{p.pk} {p.name}")

cat = PartCategory.objects.get(pk=136)  # Hardware
print(f"category: {cat.pathstring}")
print(f"part    : {NAME}")
print(f"PO      : Amazon {ORDER} issue {ISSUE}, 1 line, qty {QTY} @ ${UNIT} PLACED")

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ---------------------------------------------------------------- part
part = dup_part.first()
if part is None:
    part = Part.objects.create(
        name=NAME, description=DESC[:250], category=cat,
        purchaseable=True, component=False, active=True,
        keywords=KEYWORDS[:250],
        link=f"https://www.amazon.com/dp/{ASIN}",
    )
    Part.objects.filter(pk=part.pk).update(notes=NOTES)
    part.refresh_from_db()
    assert part.keywords and part.notes, "part fields did not stick"
    print(f"CREATED part #{part.pk}")
else:
    print(f"REUSED part #{part.pk}")

# ---------------------------------------------------------------- supplier part
sp = dup_sp.first()
if sp is None:
    sp = SupplierPart(supplier=amazon, part=part, SKU=ASIN,
                      link=f"https://www.amazon.com/dp/{ASIN}",
                      note="Sold by Hecfu-US. Listing is '1 Pack' = one lock.")
    sp.pack_quantity = "1"
    sp.save()  # .save() not .update(): only pack_quantity_native is read at receive
    sp.refresh_from_db()
    assert float(sp.pack_quantity_native) == 1.0, "pack native did not stick"
    print(f"CREATED SupplierPart #{sp.pk} pack_native={sp.pack_quantity_native}")
else:
    print(f"REUSED SupplierPart #{sp.pk}")

# ---------------------------------------------------------------- purchase order
po = PurchaseOrder(
    supplier=amazon,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=f"Amazon order {ORDER} — 5/8 in keyed-alike cam lock",
    issue_date=ISSUE,
    status=PurchaseOrderStatus.PLACED.value,
    notes=("Auto-created from the Amazon order-confirmation email of 2026-09-11 "
           "(queue C sweep 2026-09-12).\n\n"
           "PRICE SOURCE: the order-details page, Item(s) Subtotal $7.69. Shipping "
           "$0.00, tax $0.00, Grand Total $7.69 — all four figures agree, which is "
           "what rules out rewards points or a gift card hiding under the grand "
           "total. The grand total itself was NOT used as the price.\n\n"
           "PLACED, not received. Arriving 2026-09-13; receive with receive_po.py "
           "when the box is physically checked in."),
)
po.save()
po.refresh_from_db()
assert po.status == PurchaseOrderStatus.PLACED.value, "PO status did not stick"
assert po.supplier_reference == ORDER, "supplier_reference did not stick"
print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status}")

li = PurchaseOrderLineItem(order=po, part=sp, quantity=QTY,
                           purchase_price=UNIT, purchase_price_currency="USD",
                           notes="Item(s) Subtotal from the Amazon order-details page.")
li.save()
li.refresh_from_db()
# Decimal comes back padded ('7.6900'), so compare numerically, not as text.
assert float(li.purchase_price.amount) == float(UNIT), \
    f"price did not stick: {li.purchase_price}"
print(f"  line: qty {li.quantity} @ {li.purchase_price} -> part #{part.pk}")

# ---------------------------------------------------------------- image
HIRES = ("https://m.media-amazon.com/images/W/BW_MEDIAX_AVIF_MEASUREMENT_1306696-T1"
         "/images/I/61ealOtrgVL._AC_SL1500_.jpg")
if part.image:
    print("image: already present — left alone")
else:
    req = urllib.request.Request(HIRES, headers={
        "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36")})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
    except Exception as exc:  # noqa: BLE001
        data = b""
        print(f"image: fetch FAILED: {exc}")
    # verify by CONTENT, never by status code: a defended host returns 200 text/html
    if data[:3] == b"\xff\xd8\xff" and len(data) > 5000:
        part.image.save(f"amazon_{ASIN}.jpg", ContentFile(data), save=True)
        part.refresh_from_db()
        assert part.image, "image did not stick"
        print(f"image: attached {len(data)} bytes -> {part.image.name}")
    elif data:
        print(f"image: REFUSED — {len(data)} bytes, magic {data[:4]!r} (not a JPEG)")

print()
print(f"DONE  part #{part.pk} | {po.reference} | image="
      f"{'Y' if Part.objects.get(pk=part.pk).image else 'n'}")
