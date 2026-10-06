"""Queue C, 22:40 daytime sweep 2026-10-05: one order -> one PO.

  Amazon 113-0317436-3273826  placed 2026-10-05, "Arriving tomorrow" (2026-10-06)
    Lasnten 3-pc cable tie tool set (opener, cutter/tensioner, steel box)
    B0DQPDCGPZ   sold by Juuqiaerw   $15.99 x1

AMAZON PRICE SOURCE -- the order-details page: Item(s) Subtotal $15.99,
shipping 0, tax 0, Rewards Points -$15.99, Grand Total $0.00.

THE GRAND TOTAL IS NOT THE PRICE. The email says "Grand Total: 0.0 USD" because
the whole order was paid with Visa points -- the exact trap the task file names.
The line carries $15.99, the per-item figure the page prints twice.

No duplicate: lookup_1005_cabletie.py on cable tie / zip tie / tie tool /
Lasnten / Juuqiaerw / cable cutter -> no tool hits (only wrap hold-downs,
springs, cables). Filed in Equipment/Hand Tools (pk 40), where the other hand
tools live; Tooling/* is machine tooling.

A 3-piece SET is one unit (an assortment is not a multipack): pack_quantity 1.
Lasnten is the listing's brand, kept in the description only -- the name says
what the thing is. No IPN, no default_location. PLACED, never received.
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

RUN = "22:40 daytime sweep 2026-10-05"
TODAY = datetime.date(2026, 10, 5)

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

AMZ_ORDER = "113-0317436-3273826"
AMZ_ASIN = "B0DQPDCGPZ"
AMZ_PRICE = "15.99"

# ------------------------------------------------------------ checks
dup = PurchaseOrder.objects.filter(Q(supplier_reference=AMZ_ORDER) | Q(reference=AMZ_ORDER))
if dup.exists():
    sys.exit(f"!! PO already exists for {AMZ_ORDER}: {[p.reference for p in dup]}")
if SupplierPart.objects.filter(SKU__iexact=AMZ_ASIN).exists():
    sys.exit(f"!! supplier part {AMZ_ASIN} already exists")

cat = PartCategory.objects.get(pk=40)
assert cat.pathstring == "Equipment/Hand Tools", cat.pathstring
print(f"category {cat.pk} {cat.pathstring}")

NAME = "Cable Tie Tool Set, 3 pc: zip-tie opener, cutter/tensioner, steel box"
DESC = ("orig: Lasnten 3 Pcs Cable Tie Tool Include 1 Zip Tie Opener, 1 Cable Cutter and "
        "Tightening Tool, and 1 Storage Box Steel Reusable Pocket Size; Amazon B0DQPDCGPZ")
KW = ("cable tie, zip tie, tie wrap, cable tie tool, zip tie tool, tie gun, tensioner, "
      "cutter, flush cutter, zip tie opener, zip tie release, wire management, Lasnten")
assert len(KW) <= 250 and len(NAME) <= 100 and len(DESC) <= 250, (len(KW), len(NAME), len(DESC))
hits = Part.objects.filter(Q(name=NAME) | Q(description__icontains=AMZ_ASIN)
                           | Q(name__icontains="cable tie tool") | Q(name__icontains="zip tie tool"))
if hits.exists():
    sys.exit(f"!! a part with this name / ASIN exists: {[h.pk for h in hits]}")

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ------------------------------------------------------------ PO
po = PurchaseOrder(
    supplier=amazon,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=AMZ_ORDER,
    description=f"Amazon order {AMZ_ORDER} — 3-pc cable tie tool set",
    issue_date=TODAY, target_date=datetime.date(2026, 10, 6),
    status=PurchaseOrderStatus.PLACED.value,
    notes=(f"Auto-created by the queue C daytime sweep, {RUN}.\n\n"
           "PRICE SOURCE: the order-details page — $15.99 for one 3-pc cable tie tool "
           "set, sold by Juuqiaerw. Item(s) Subtotal $15.99, shipping $0.00, tax $0.00, "
           "Rewards Points -$15.99, Grand Total $0.00.\n\n"
           "The $0.00 grand total is cash after Visa points were applied as a PAYMENT "
           "METHOD. It is not the price and is deliberately not on the line.\n\n"
           "PLACED, not received."),
)
po.save()
po.refresh_from_db()
assert po.status == PurchaseOrderStatus.PLACED.value
assert po.supplier_reference == AMZ_ORDER and po.reference != AMZ_ORDER
print(f"\nCREATED {po.reference} supplier_ref={po.supplier_reference}")

part = Part(
    name=NAME, description=DESC, category=cat, keywords=KW,
    component=False, purchaseable=True, assembly=False,
    notes=("Three-piece hand tool set for nylon cable ties: a zip-tie opener (releases "
           "the pawl so a tie can be reused), a combined tensioner/flush cutter, and a "
           "steel pocket storage box. Counted as ONE set, not three pieces.\n\n"
           f"Created by the queue C daytime sweep, {RUN}, from Amazon order "
           f"{AMZ_ORDER}."),
)
part.save()
part.refresh_from_db()
assert part.name == NAME and part.category_id == cat.pk and part.keywords == KW
print(f"CREATED part #{part.pk} {part.name}  cat={part.category.pathstring}")

sp = SupplierPart(supplier=amazon, part=part, SKU=AMZ_ASIN,
                  link=f"https://www.amazon.com/dp/{AMZ_ASIN}",
                  description="Lasnten 3-pc cable tie tool set (Juuqiaerw)")
sp.pack_quantity = "1"
sp.save()
sp.refresh_from_db()
assert sp.SKU == AMZ_ASIN and sp.part_id == part.pk, "sp did not stick"
print(f"  sp #{sp.pk} SKU={sp.SKU} -> part #{part.pk}")

li = PurchaseOrderLineItem(
    order=po, part=sp, quantity=1,
    purchase_price=AMZ_PRICE, purchase_price_currency="USD",
    notes="Per-item price from the Amazon order-details page ($15.99), NOT the "
          "$0.00 grand total (paid entirely with rewards points).")
li.save()
li.refresh_from_db()
assert float(li.purchase_price.amount) == float(AMZ_PRICE), li.purchase_price
print(f"  line qty {li.quantity} @ {li.purchase_price}")

po.refresh_from_db()
print(f"{po.reference} {po.supplier.name} {po.supplier_reference} status={po.status} "
      f"lines={po.lines.count()}")
