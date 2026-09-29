"""Queue C, 12:40 sweep 2026-09-29: two orders -> two POs.

  Amazon 113-9034798-2737037  placed 2026-09-29, "Arriving Thursday" (2026-10-01)
    Brother RQL-810W (QL-810W) Label Printer, Wireless, White (Renewed)
    B07MDHL97G  sold by Amazon.com  $129.99

  Haas Tooling 1000520353     placed 2026-09-29, "1 Day - Free" shipping
    03-3399  1/2" Dia. Carbide Straight Tooth Keyseat Cutter, 10 Flute,
             Uncoated, 1/2" Smooth Shank x 1/8" Cut Width   qty 1  $89.95

AMAZON PRICE SOURCE -- the order-details page: Item(s) Subtotal $129.99,
shipping 0, tax 0, Rewards Points -$2.49, Grand Total $127.50. The email's
$127.50 is the points-reduced total and was NOT used.

THE PRINTER IS A SUPPLIER PART ON #1057, NOT A NEW PART. #1057 "Brother QL-810W
Label Printer, wireless" is the model; this is a second unit of it, bought
renewed. Renewed is a condition of one unit, not a different part -- and #1057
is trackable, so each machine is its own serialised stock row and the
condition goes on that row at receive. A separate "QL-810W (Renewed)" part
would split one model across two parts and hide it from "do we own one?".
ASIN B07MDHL97G is not on any supplier part (probe_0929_1240.py). The existing
sp #685 carries a placeholder SKU AMZ-QL810W; left alone.

HAAS PRICE -- Haas quotes extended price; qty 1 so the line price IS the unit
price: $89.95 as printed. The mail also shows "Order Discounts -$9.00" and
"Winner's Circle Discount -$9.00", and the TOTAL $80.95 = 89.95 - 9.00, so that
is ONE $9.00 discount printed twice (the category line and its breakdown), not
$18. Booked the line at the verbatim $89.95 and put the discount and the
$80.95 actually paid in the PO notes. Rejected writing $80.95 on the line: it
is a derived per-item figure, and the standing rule is only a price printed on
an order line. It is exact here (one line takes the whole discount), so Scott
can overwrite it if he wants paid-cost on the line.

THE CUTTER IS A NEW PART. Only keyseat hit is #409, an HSS T-slot/Woodruff
cutter from Amazon (B09ZKPGVFH) -- different material, maker and size. Filed
in flat Tooling/Endmills beside #409 and the Haas chamfer mill #114 (the flat
side of the shadow roots, per the precedent of both). Naming follows #114.

This is the FIRST Haas Tooling PO on the instance: the six earlier Haas parts
arrived without one.

No image (02:05 job). No default_location. PLACED, never received.
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
from part.models import Part, PartCategory  # noqa: E402

RUN = "12:40 run 2026-09-29"
TODAY = datetime.date(2026, 9, 29)

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")
haas = Company.objects.get(pk=5)
assert haas.name == "Haas Tooling", haas.name

AMZ_ORDER = "113-9034798-2737037"
AMZ_ASIN = "B07MDHL97G"
AMZ_PRICE = "129.99"
HAAS_ORDER = "1000520353"
HAAS_SKU = "03-3399"
HAAS_PRICE = "89.95"

# ------------------------------------------------------------ checks
for ref in (AMZ_ORDER, HAAS_ORDER):
    dup = PurchaseOrder.objects.filter(Q(supplier_reference=ref) | Q(reference=ref))
    if dup.exists():
        sys.exit(f"!! PO already exists for {ref}: {[p.reference for p in dup]}")

printer = Part.objects.get(pk=1057)
assert printer.name.startswith("Brother QL-810W"), printer.name
assert printer.trackable, "#1057 is expected to be trackable"
if SupplierPart.objects.filter(SKU__iexact=AMZ_ASIN).exists():
    sys.exit(f"!! supplier part {AMZ_ASIN} already exists")
print(f"printer part #{printer.pk} {printer.name!r} stock={printer.total_stock}")

if SupplierPart.objects.filter(SKU__iexact=HAAS_SKU).exists():
    sys.exit(f"!! supplier part {HAAS_SKU} already exists")
CUT_NAME = '1/2" Carbide Keyseat Cutter, 10FL, 1/8" Cut Width, Uncoated'
CUT_DESC = ('orig: 1/2" Dia. Carbide Straight Tooth Keyseat Cutter, 10 Flute, '
            'Uncoated, 1/2" Smooth Shank x 1/8" Cut Width; Haas P/N 03-3399; '
            'ordered 2026-09-29')
CUT_KW = ("keyseat cutter, keyseat, keyway cutter, woodruff, T-slot, slotting "
          "cutter, undercut, side cutter, 1/2 inch, 1/8 cut width, 0.125, carbide, "
          "straight tooth, 10 flute, uncoated, 1/2 shank, Haas, 03-3399")
assert len(CUT_KW) <= 250 and len(CUT_NAME) <= 100
if Part.objects.filter(Q(name=CUT_NAME) | Q(description__icontains="03-3399")
                       | Q(IPN__iexact=HAAS_SKU)).exists():
    sys.exit("!! a part with this name / Haas P/N exists")
cats = [c for c in PartCategory.objects.filter(name="Endmills")
        if c.pathstring == "Tooling/Endmills"]
assert len(cats) == 1, cats
cat = cats[0]

# Haas link: derive from sp #14 (03-0612) the way the image job does.
ref_sp = SupplierPart.objects.get(pk=14)
haas_link = ""
if ref_sp.link and "03-0612" in ref_sp.link:
    haas_link = ref_sp.link.replace("03-0612", HAAS_SKU)
print(f"haas link: {haas_link or '(none derivable; sp #14 link=' + repr(ref_sp.link) + ')'}")
print(f"cutter -> category #{cat.pk} {cat.pathstring} ({cat.parts.count()} parts)")

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ------------------------------------------------------------ Amazon PO
po = PurchaseOrder(
    supplier=amazon,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=AMZ_ORDER,
    description=f"Amazon order {AMZ_ORDER} — Brother QL-810W label printer (Renewed)",
    issue_date=TODAY, target_date=datetime.date(2026, 10, 1),
    status=PurchaseOrderStatus.PLACED.value,
    notes=(f"Auto-created by the queue C daytime sweep, {RUN}.\n\n"
           "PRICE SOURCE: the order-details page — $129.99 for one Brother "
           "RQL-810W (QL-810W) label printer, Renewed, sold by Amazon.com. Item(s) "
           "Subtotal $129.99, shipping $0.00, tax $0.00, Rewards Points -$2.49, "
           "Grand Total $127.50. The email's $127.50 is the points-reduced total "
           "and was not used as a price.\n\n"
           "A SECOND QL-810W: booked against the existing part #1057 (trackable) "
           "via a new supplier part for ASIN B07MDHL97G. The unit already in stock "
           "is serial U64633C6G919420 at the electronics bench.\n\n"
           "RECEIVING NEEDS THE NEW UNIT'S SERIAL NUMBER (#1057 is serialised) — "
           "read it off the printer's label. Note 'Renewed' on the stock row.\n\n"
           "PLACED, not received."),
)
po.save()
po.refresh_from_db()
assert po.status == PurchaseOrderStatus.PLACED.value
assert po.supplier_reference == AMZ_ORDER and po.reference != AMZ_ORDER
print(f"\nCREATED {po.reference} supplier_ref={po.supplier_reference}")

sp = SupplierPart(supplier=amazon, part=printer, SKU=AMZ_ASIN,
                  link=f"https://www.amazon.com/dp/{AMZ_ASIN}",
                  description="Amazon Renewed listing: Brother RQL-810W (QL-810W), white")
sp.pack_quantity = "1"
sp.save()
sp.refresh_from_db()
assert sp.SKU == AMZ_ASIN and sp.part_id == printer.pk, "sp did not stick"
print(f"  sp #{sp.pk} SKU={sp.SKU} -> part #{printer.pk}")

li = PurchaseOrderLineItem(
    order=po, part=sp, quantity=1,
    purchase_price=AMZ_PRICE, purchase_price_currency="USD",
    notes="Per-item price from the Amazon order-details page ($129.99, Renewed).")
li.save()
li.refresh_from_db()
assert float(li.purchase_price.amount) == float(AMZ_PRICE), li.purchase_price
print(f"  line qty {li.quantity} @ {li.purchase_price}")

# ------------------------------------------------------------ Haas PO
po2 = PurchaseOrder(
    supplier=haas,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=HAAS_ORDER,
    description=f"Haas Tooling order {HAAS_ORDER} — 1/2\" carbide keyseat cutter 03-3399",
    issue_date=TODAY, target_date=datetime.date(2026, 9, 30),
    status=PurchaseOrderStatus.PLACED.value,
    notes=(f"Auto-created by the queue C daytime sweep, {RUN}.\n\n"
           "PRICE SOURCE: the Haas order-confirmation email — 03-3399 qty 1, "
           "$89.95 (Haas prints extended price; qty 1 so it is the unit price). "
           "Subtotal $89.95, Order Discounts -$9.00 (itemised as Winner's Circle "
           "Discount -$9.00 — one discount printed twice, not $18), tax $0.00, "
           "shipping '1 Day - Free', TOTAL $80.95.\n\n"
           "The line is booked at the printed $89.95. Actual paid cost for the "
           "cutter is $80.95 after the Winner's Circle discount; overwrite the "
           "line if paid cost is wanted.\n\n"
           "First Haas Tooling PO on this instance — earlier Haas parts arrived "
           "without one.\n\nPLACED, not received."),
)
po2.save()
po2.refresh_from_db()
assert po2.status == PurchaseOrderStatus.PLACED.value
assert po2.supplier_reference == HAAS_ORDER and po2.reference != HAAS_ORDER
print(f"\nCREATED {po2.reference} supplier_ref={po2.supplier_reference}")

part = Part(
    name=CUT_NAME, description=CUT_DESC, category=cat, keywords=CUT_KW,
    component=True, purchaseable=True, assembly=False,
    notes=('Solid carbide straight-tooth keyseat (Woodruff/T-slot style) cutter: '
           '1/2" cutting diameter, 1/8" cut width, 10 flutes, uncoated, 1/2" smooth '
           'shank. For keyways, undercuts and side slots.\n\n'
           'NOT the same part as #409 (an HSS T-slot/Woodruff cutter from Amazon).\n\n'
           f'Created by the queue C daytime sweep, {RUN}, from Haas Tooling order '
           f'{HAAS_ORDER}.'),
)
part.save()
part.refresh_from_db()
assert part.name == CUT_NAME and part.category_id == cat.pk and part.keywords == CUT_KW
print(f"CREATED part #{part.pk} {part.name}  cat={part.category.pathstring}")

sp2 = SupplierPart(supplier=haas, part=part, SKU=HAAS_SKU, link=haas_link)
sp2.pack_quantity = "1"
sp2.save()
sp2.refresh_from_db()
assert sp2.SKU == HAAS_SKU and sp2.part_id == part.pk
print(f"  sp #{sp2.pk} SKU={sp2.SKU} link={sp2.link!r}")

li2 = PurchaseOrderLineItem(
    order=po2, part=sp2, quantity=1,
    purchase_price=HAAS_PRICE, purchase_price_currency="USD",
    notes="Line price as printed on the Haas confirmation ($89.95, before the "
          "$9.00 Winner's Circle order discount).")
li2.save()
li2.refresh_from_db()
assert float(li2.purchase_price.amount) == float(HAAS_PRICE), li2.purchase_price
print(f"  line qty {li2.quantity} @ {li2.purchase_price}")

for p in (po, po2):
    p.refresh_from_db()
    print(f"{p.reference} {p.supplier.name} {p.supplier_reference} status={p.status} "
          f"lines={p.lines.count()}")
