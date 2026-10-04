"""Queue C, 02:05 run 2026-10-04: Haas Tooling order 1000523832 -> one PO.

  Placed 2026-10-03 (mail 2026-10-04 03:11Z = 23:11 EDT 10-03), "1 Day - Free".

  SKU      qty  printed   unit    what
  03-0570   2   $51.90   25.95   3/8 3FL 1" LOC 0.015R
  03-0085   2   $59.94   29.97   3/8 3FL 7/8" LOC square
  03-0392   2   $83.94   41.97   3/8 3FL 1-1/2" LOC square
  03-0575   2   $83.94   41.97   1/2 3FL 1-1/4" LOC 0.12R
  03-0086   2   $59.94   29.97   1/2 3FL 1" LOC square
  03-0613   1   $26.97   26.97   3/8 45deg chamfer mill
  03-0612   1   $17.97   17.97   1/4 45deg chamfer mill   <- REORDER of #114 (sp #14)
  03-0611   1   $10.97   10.97   1/8 45deg chamfer mill

PRINTED PRICE IS EXTENDED, and this order proves it rather than assuming it.
The eight printed figures sum to $395.57. Read as unit prices they would make a
$735.23 order against a $452.35 subtotal -- impossible. Read as extended, the
reconciliation closes to the cent: subtotal $452.35 is LIST, the lines are sale
prices ($56.78 below list), and "Order Discounts -$96.34" = that $56.78 plus
"Winner's Circle Discount -$39.56", which is exactly 10% of $395.57. TOTAL
$356.01. (The 09-29 order, PO-0186, fits the same 10%: $9.00 on $89.95.)

Lines are booked at printed/qty -- the order-line figure, not the post-discount
paid cost. Rejected spreading the $39.56 across lines: it is a derived figure
and the standing rule is only a price printed on an order line. The 10% and the
paid total go in the PO notes so paid cost is one multiplication away.

03-0612 IS NOT A NEW PART: sp #14 -> #114 '1/4" 45deg Carbide Chamfer Mill, 2FL,
TiCN, 1/8" LOC' already carries it (stock 1). The line goes on sp #14.

SEVEN NEW PARTS. No SKU, IPN, description or name hit for any of them
(probe_1004_0205.py), and none of the 34 end-mill/chamfer parts is a Haas
3-flute of these sizes. Filed in flat Tooling/Endmills beside #114 and #1265,
named in #114's shape; IPN = Haas P/N as on #114 and the other Haas parts.
Link in the house Haas shape (search?q=<SKU>), same as every Haas sp.

No image (queue A does that). No default_location. PLACED, never received.
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

RUN = "02:05 run 2026-10-04"
ORDER = "1000523832"
PLACED = datetime.date(2026, 10, 3)
TARGET = datetime.date(2026, 10, 5)

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

haas = Company.objects.get(pk=5)
assert haas.name == "Haas Tooling", haas.name

# sku, qty, printed extended, name, orig title, keywords
NEW = [
    ("03-0570", 2, "51.90",
     '3/8" Carbide End Mill, 3FL, 1" LOC, 0.015" Corner Radius, Uncoated',
     '3/8" Ø Carbide End Mill, 3 Flute, Uncoated, 3/8" Shank x 1" LOC, 0.015" Radius, HSAM2',
     "end mill, endmill, 3/8 inch, 0.375, 3 flute, corner radius, radiused, bull nose, "
     "0.015 radius, carbide, uncoated, aluminum, 3/8 shank, 1 inch LOC, Haas, 03-0570"),
    ("03-0085", 2, "59.94",
     '3/8" Carbide End Mill, 3FL, 7/8" LOC, Square, Uncoated',
     '3/8" Ø Carbide End Mill, 3 Flute, Uncoated, 3/8" Shank x 7/8" LOC, Square Profile, HSAM2',
     "end mill, endmill, 3/8 inch, 0.375, 3 flute, square end, flat end, carbide, "
     "uncoated, aluminum, 3/8 shank, 7/8 LOC, Haas, 03-0085"),
    ("03-0392", 2, "83.94",
     '3/8" Carbide End Mill, 3FL, 1-1/2" LOC, Square, Uncoated',
     '3/8" Ø Carbide End Mill, 3 Flute, Uncoated, 3/8" Shank x 1-1/2" LOC, Square Profile, HSAM1',
     "end mill, endmill, 3/8 inch, 0.375, 3 flute, long flute, long length, square end, "
     "flat end, carbide, uncoated, aluminum, 3/8 shank, 1-1/2 LOC, Haas, 03-0392"),
    ("03-0575", 2, "83.94",
     '1/2" Carbide End Mill, 3FL, 1-1/4" LOC, 0.12" Corner Radius, Uncoated',
     '1/2" Ø Carbide End Mill, 3 Flute, Uncoated, 1/2" Shank x 1-1/4" LOC, 0.12" Radius, HSAM2',
     "end mill, endmill, 1/2 inch, 0.500, 3 flute, corner radius, radiused, bull nose, "
     "0.12 radius, carbide, uncoated, aluminum, 1/2 shank, 1-1/4 LOC, Haas, 03-0575"),
    ("03-0086", 2, "59.94",
     '1/2" Carbide End Mill, 3FL, 1" LOC, Square, Uncoated',
     '1/2" Ø Carbide End Mill, 3 Flute, Uncoated, 1/2" Shank x 1" LOC, Square Profile, HSAM2',
     "end mill, endmill, 1/2 inch, 0.500, 3 flute, square end, flat end, carbide, "
     "uncoated, aluminum, 1/2 shank, 1 inch LOC, Haas, 03-0086"),
    ("03-0613", 1, "26.97",
     '3/8" 45° Carbide Chamfer Mill, 2FL, TiCN, 3/16" LOC',
     '3/8" Dia. 45° Carbide Chamfer Mill, 2 Flute, TiCN Coated, 3/16" LOC x 2-1/2" Overall Length, HSAM1',
     "chamfer mill, chamfer, 45 degree, 90 degree included, deburr, deburring, edge break, "
     "countersink, spot, 3/8 inch, 2 flute, carbide, TiCN, Haas, 03-0613"),
    ("03-0611", 1, "10.97",
     '1/8" 45° Carbide Chamfer Mill, 2FL, TiCN, 1/16" LOC',
     '1/8" Dia. 45° Carbide Chamfer Mill, 2 Flute, TiCN Coated, 1/16" LOC x 1-1/2" Overall Length, HSAM1',
     "chamfer mill, chamfer, 45 degree, 90 degree included, deburr, deburring, edge break, "
     "countersink, spot, 1/8 inch, 2 flute, carbide, TiCN, Haas, 03-0611"),
]
REORDER = ("03-0612", 1, "17.97", 14, 114)
ORDER_OF_LINES = ["03-0570", "03-0085", "03-0392", "03-0575", "03-0086",
                  "03-0613", "03-0612", "03-0611"]

# ------------------------------------------------------------ checks
dup = PurchaseOrder.objects.filter(Q(supplier_reference=ORDER) | Q(reference=ORDER))
if dup.exists():
    sys.exit(f"!! PO already exists for {ORDER}: {[p.reference for p in dup]}")

total = sum(float(x[2]) for x in NEW) + float(REORDER[2])
assert abs(total - 395.57) < 0.005, total

for sku, qty, ext, name, orig, kw in NEW:
    assert len(name) <= 100 and len(kw) <= 250, (sku, len(name), len(kw))
    if SupplierPart.objects.filter(SKU__iexact=sku).exists():
        sys.exit(f"!! supplier part {sku} already exists")
    if Part.objects.filter(Q(name=name) | Q(IPN__iexact=sku)
                           | Q(description__icontains=sku)).exists():
        sys.exit(f"!! a part with name/IPN/description for {sku} exists")

sku, qty, ext, sp_pk, part_pk = REORDER
sp14 = SupplierPart.objects.get(pk=sp_pk)
assert sp14.SKU == sku and sp14.part_id == part_pk and sp14.supplier_id == haas.pk
assert str(sp14.pack_quantity) == "1", sp14.pack_quantity

cats = [c for c in PartCategory.objects.filter(name="Endmills")
        if c.pathstring == "Tooling/Endmills"]
assert len(cats) == 1, cats
cat = cats[0]

ref = PurchaseOrder.generate_reference()
print(f"would create {ref} for Haas {ORDER}; cat #{cat.pk} {cat.pathstring}")
for sku, qty, ext, name, *_ in NEW:
    print(f"  NEW  {sku} qty {qty} @ {float(ext)/qty:.2f}  {name}")
print(f"  REORDER {REORDER[0]} -> sp #{sp_pk} part #{part_pk} qty 1 @ {REORDER[2]}")

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ------------------------------------------------------------ PO
po = PurchaseOrder(
    supplier=haas,
    reference=ref,
    supplier_reference=ORDER,
    description=(f"Haas Tooling order {ORDER} — 3/8\" and 1/2\" 3FL carbide end mills "
                 "(x10) + three 45° chamfer mills"),
    issue_date=PLACED, target_date=TARGET,
    status=PurchaseOrderStatus.PLACED.value,
    notes=(f"Auto-created by the overnight queue C sweep, {RUN}.\n\n"
           "PRICE SOURCE: the Haas order-confirmation email. Haas prints EXTENDED "
           "price; each line is booked at printed/qty.\n\n"
           "Reconciliation: the eight printed lines sum to $395.57 (sale prices). "
           "Subtotal $452.35 is LIST. Order Discounts -$96.34 = $56.78 list-to-sale "
           "+ Winner's Circle Discount -$39.56 (10% of $395.57). Tax $0.00, shipping "
           "'1 Day - Free'. TOTAL $356.01.\n\n"
           "Lines are at the printed sale price, before the 10% Winner's Circle "
           "discount. Paid cost per item = line price x 0.90.\n\n"
           "03-0612 is a REORDER of #114 (sp #14); the other seven SKUs are new parts "
           "created by this sweep.\n\nPLACED, not received."),
)
po.save()
po.refresh_from_db()
assert po.status == PurchaseOrderStatus.PLACED.value
assert po.supplier_reference == ORDER and po.reference == ref
print(f"\nCREATED {po.reference} supplier_ref={po.supplier_reference}")

made = {}
for sku, qty, ext, name, orig, kw in NEW:
    part = Part(
        name=name, IPN=sku, category=cat, keywords=kw,
        description=f"orig: {orig}; Haas P/N {sku}; ordered 2026-10-03",
        link=f"https://www.haastooling.com/search?q={sku}",
        component=True, purchaseable=True, assembly=False,
        notes=(f"Created by the overnight queue C sweep, {RUN}, from Haas Tooling "
               f"order {ORDER}. HSAM1/HSAM2 in the Haas title is carried verbatim "
               "in the description; not interpreted."),
    )
    part.save()
    part.refresh_from_db()
    assert part.name == name and part.IPN == sku and part.keywords == kw \
        and part.category_id == cat.pk, f"part {sku} did not stick"
    sp = SupplierPart(supplier=haas, part=part, SKU=sku,
                      link=f"https://www.haastooling.com/search?q={sku}",
                      description=orig[:250])
    sp.pack_quantity = "1"
    sp.save()
    sp.refresh_from_db()
    assert sp.SKU == sku and sp.part_id == part.pk and float(sp.pack_quantity_native) == 1
    made[sku] = (part, sp, qty, ext)
    print(f"  CREATED part #{part.pk} {name}  sp #{sp.pk}")

made[REORDER[0]] = (sp14.part, sp14, REORDER[1], REORDER[2])

for sku in ORDER_OF_LINES:
    part, sp, qty, ext = made[sku]
    unit = f"{float(ext) / qty:.2f}"
    li = PurchaseOrderLineItem(
        order=po, part=sp, quantity=qty,
        purchase_price=unit, purchase_price_currency="USD",
        notes=(f"Haas printed ${ext} extended for qty {qty}; unit {unit} "
               "(sale price, before the 10% Winner's Circle discount)."))
    li.save()
    li.refresh_from_db()
    assert float(li.purchase_price.amount) == float(unit), li.purchase_price
    print(f"  line {sku} qty {li.quantity} @ {li.purchase_price}  -> part #{part.pk}")

po.refresh_from_db()
lines = list(po.lines.all())
s = sum(float(l.purchase_price.amount) * float(l.quantity) for l in lines)
print(f"\n{po.reference} status={po.status} lines={len(lines)} sum={s:.2f} (expect 395.57)")
assert len(lines) == 8 and abs(s - 395.57) < 0.005
