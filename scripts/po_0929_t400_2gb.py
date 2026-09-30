"""Queue C, 22:40 sweep 2026-09-29: one order -> one PO.

  Amazon 113-1489119-5361851  placed 2026-09-29, "Arriving Thursday" (2026-10-01)
    PNY NVIDIA T400   B09DG5B78Z   sold by Computer Nation Store   $218.00

AMAZON PRICE SOURCE -- the order-details page: Item(s) Subtotal $218.00,
shipping 0, tax 0, no points, Grand Total $218.00. One item, qty 1.

THIS IS A NEW PART, NOT A SECOND SUPPLIER ON #1215. #1215 is "NVIDIA T400 4GB
GDDR6" from eBay order 06-15193-19595 (PO-0176) -- which the seller CANCELED
today, refund $118.00, so this Amazon order looks like its replacement. The
obvious move was a supplier part on #1215. Rejected because the listing's own
detail table reads "Graphics Card Ram 2 GB", "Model Number VCNT400-PB", and
VCNT400-PB is PNY's 2 GB T400 (the 4 GB is a different PNY model). A 2 GB and
a 4 GB card are not interchangeable stock, and merging them would make "do we
own a 4 GB T400?" answer yes wrongly.

Naming follows #1215 but leaves out "Low Profile" and "3x Mini DisplayPort":
this listing states DisplayPort 1.4 and three displays but not the bracket or
the connector size, and nothing here goes on the name that the listing did not
say. Filed in Modules beside #1215.

PO-0176 is NOT touched here (cancelling a PO is not a sweep action) -- it goes
on the decision queue.

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
from part.models import Part  # noqa: E402

RUN = "22:40 run 2026-09-29"
TODAY = datetime.date(2026, 9, 29)

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

AMZ_ORDER = "113-1489119-5361851"
AMZ_ASIN = "B09DG5B78Z"
AMZ_PRICE = "218.00"
MPN = "VCNT400-PB"

# ------------------------------------------------------------ checks
dup = PurchaseOrder.objects.filter(Q(supplier_reference=AMZ_ORDER) | Q(reference=AMZ_ORDER))
if dup.exists():
    sys.exit(f"!! PO already exists for {AMZ_ORDER}: {[p.reference for p in dup]}")
if SupplierPart.objects.filter(SKU__iexact=AMZ_ASIN).exists():
    sys.exit(f"!! supplier part {AMZ_ASIN} already exists")

ref_part = Part.objects.get(pk=1215)
assert "T400 4GB" in ref_part.name, ref_part.name
cat = ref_part.category
print(f"sibling #{ref_part.pk} {ref_part.name!r} cat={cat.pathstring}")

NAME = "NVIDIA T400 2GB GDDR6 Graphics Card, PNY VCNT400-PB"
DESC = ("orig: PNY NVIDIA T400 (Amazon B09DG5B78Z; listing details: 2 GB GDDR6, "
        "PCIe x16, DisplayPort, Model VCNT400-PB, UPC 751492646350); ordered 2026-09-29")
KW = ("NVIDIA, T400, Quadro, PNY, VCNT400-PB, GPU, graphics card, video card, GDDR6, "
      "2GB, PCIe, PCI Express, x16, DisplayPort, DP 1.4, multi-monitor, triple head, "
      "workstation, Turing, TU117")
assert len(KW) <= 250 and len(NAME) <= 100 and len(DESC) <= 250
hits = Part.objects.filter(Q(name=NAME) | Q(description__icontains=MPN)
                           | Q(IPN__iexact=MPN) | Q(keywords__icontains=MPN))
if hits.exists():
    sys.exit(f"!! a part with this name / MPN exists: {[h.pk for h in hits]}")

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ------------------------------------------------------------ PO
po = PurchaseOrder(
    supplier=amazon,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=AMZ_ORDER,
    description=f"Amazon order {AMZ_ORDER} — PNY NVIDIA T400 2GB (VCNT400-PB)",
    issue_date=TODAY, target_date=datetime.date(2026, 10, 1),
    status=PurchaseOrderStatus.PLACED.value,
    notes=(f"Auto-created by the queue C daytime sweep, {RUN}.\n\n"
           "PRICE SOURCE: the order-details page — $218.00 for one PNY NVIDIA T400, "
           "sold by Computer Nation Store. Item(s) Subtotal $218.00, shipping $0.00, "
           "tax $0.00, Grand Total $218.00.\n\n"
           "2 GB CARD, NOT THE 4 GB: the listing reads 'Graphics Card Ram 2 GB' and "
           "'Model Number VCNT400-PB'. Booked as a new part rather than on #1215 "
           "(the 4 GB T400). CHECK THE BOX LABEL AT RECEIVE — if it is actually the "
           "4 GB card, move this line to #1215 and retire the new part.\n\n"
           "Apparently replaces eBay order 06-15193-19595 (PO-0176, 4 GB T400, "
           "$118.00), which the seller canceled 2026-09-29 at the buyer's request.\n\n"
           "PLACED, not received."),
)
po.save()
po.refresh_from_db()
assert po.status == PurchaseOrderStatus.PLACED.value
assert po.supplier_reference == AMZ_ORDER and po.reference != AMZ_ORDER
print(f"\nCREATED {po.reference} supplier_ref={po.supplier_reference}")

part = Part(
    name=NAME, description=DESC, category=cat, keywords=KW,
    component=True, purchaseable=True, assembly=False,
    notes=("NVIDIA T400 workstation graphics card, PNY board, 2 GB GDDR6 "
           "(PNY model VCNT400-PB).\n\n"
           "NOT the same part as #1215 (the 4 GB T400).\n\n"
           f"Created by the queue C daytime sweep, {RUN}, from Amazon order "
           f"{AMZ_ORDER}."),
)
part.save()
part.refresh_from_db()
assert part.name == NAME and part.category_id == cat.pk and part.keywords == KW
print(f"CREATED part #{part.pk} {part.name}  cat={part.category.pathstring}")

sp = SupplierPart(supplier=amazon, part=part, SKU=AMZ_ASIN,
                  link=f"https://www.amazon.com/dp/{AMZ_ASIN}",
                  description="PNY NVIDIA T400 (VCNT400-PB, 2 GB)")
sp.pack_quantity = "1"
sp.save()
sp.refresh_from_db()
assert sp.SKU == AMZ_ASIN and sp.part_id == part.pk, "sp did not stick"
print(f"  sp #{sp.pk} SKU={sp.SKU} -> part #{part.pk}")

li = PurchaseOrderLineItem(
    order=po, part=sp, quantity=1,
    purchase_price=AMZ_PRICE, purchase_price_currency="USD",
    notes="Per-item price from the Amazon order-details page ($218.00).")
li.save()
li.refresh_from_db()
assert float(li.purchase_price.amount) == float(AMZ_PRICE), li.purchase_price
print(f"  line qty {li.quantity} @ {li.purchase_price}")

po.refresh_from_db()
print(f"{po.reference} {po.supplier.name} {po.supplier_reference} status={po.status} "
      f"lines={po.lines.count()}")
