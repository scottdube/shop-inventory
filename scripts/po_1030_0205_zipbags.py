"""Queue C, 02:05 overnight run 2026-10-30: one Amazon reorder -> one PO, two lines.

  113-9489932-9591402  placed 2026-10-29 23:02 ET (after the 22:40 sweep), ship to The
  Villages FL (LRD), "Arriving tomorrow" on the order page read 2026-10-30 02:1x
    1. Small Plastic Bags 2x3, 400pcs (JINYONBAG)              $7.99  qty 1
    2. Aubeco 400Pcs 3x4 Inch Clear Plastic Zip Bags, 2Mil     $9.99  qty 1

IN, not classified: both titles are the listings already on parts 850/851 (Part.link
B09N32PLTN, B09MCM8QGK; titles matched in the 2026-09-17 image run), so this is a reorder.
Their Amazon supplier parts #559/#560 carry brand SKUs (JINYONBAG-2x3, Aubeco-3x4), not
the ASIN -- the first dry run looked up by ASIN and found nothing. The DECLINED line for Aubeco zip bags names one
specific order (113-8174373-8737051), not the category, so it does not cover this one.

PRICES are the per-item prices on the order-details page. Grand total was $0.00 (gift card
$19.24 applied) and is NOT a price. Price is per supplier-part unit = per 400-bag listing;
pack_quantity stays 1 because zip-bag-pack-quantity-400-vs-1 is still open -- not ours to
settle here.

Dry run prints the matched supplier parts. --commit writes. PLACED, never received.
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
from plugins.notes_compat import note_set, note_text  # noqa: E402

RUN = "02:05 overnight run 2026-10-30"
ORDER = "113-9489932-9591402"
TODAY = datetime.date(2026, 10, 29)
ARRIVE = datetime.date(2026, 10, 31)
LINES = [
    dict(asin="B09N32PLTN", sku="JINYONBAG-2x3", part=850, qty=1, price="7.99",
         title="Small Plastic Bags 2x3, 400pcs (JINYONBAG)"),
    dict(asin="B09MCM8QGK", sku="Aubeco-3x4", part=851, qty=1, price="9.99",
         title="Aubeco 400Pcs 3x4 Inch Clear Plastic Zip Bags, 2Mil"),
]
PO_DESC = (f"Amazon order {ORDER} — zip bags 2x3 + 3x4, 400-bag listings, reorder "
           "(to The Villages FL)")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")
dup = PurchaseOrder.objects.filter(Q(supplier_reference=ORDER) | Q(reference=ORDER))
if dup.exists():
    sys.exit(f"!! PO already exists for {ORDER}: {[p.reference for p in dup]}")

sps = []
for L in LINES:
    # These supplier parts carry a brand SKU, not the ASIN; the ASIN is on Part.link.
    sp = SupplierPart.objects.filter(supplier=amazon, SKU__iexact=L["sku"]).first()
    assert sp, f"no Amazon supplier part {L['sku']}"
    p = sp.part
    assert L["asin"] in (p.link or ""), f"part #{p.pk} link {p.link} lacks {L['asin']}"
    print(f"  {L['asin']}: sp #{sp.pk} -> part #{p.pk} {p.name!r} active={p.active} "
          f"pack={sp.pack_quantity} native={sp.pack_quantity_native} img={'Y' if p.image else 'N'} "
          f"kw={'Y' if p.keywords else 'N'}")
    assert p.pk == L["part"], f"{L['asin']} is on part #{p.pk}, expected #{L['part']}"
    sps.append(sp)

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --commit")

po = PurchaseOrder(
    supplier=amazon,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=PO_DESC,
    issue_date=TODAY, target_date=ARRIVE,
    status=PurchaseOrderStatus.PLACED.value,
)
po.save()
po.refresh_from_db()
assert po.supplier_id == amazon.pk and po.supplier_reference == ORDER
assert po.status == PurchaseOrderStatus.PLACED.value and po.reference != ORDER
note_set(po, (f"Auto-created by the overnight enrich run, {RUN}.\n\n"
              "Ships to The Villages FL (LRD). Reorder of the zip bags on parts 850/851.\n\n"
              "Line prices read from the Amazon order-details page: $7.99 + $9.99 = item "
              "subtotal $17.98, tax $1.26. Grand total $0.00 because a $19.24 gift card was "
              "applied -- a payment method, not a discount, and not a price.\n\n"
              "Price is per 400-bag listing; supplier-part pack_quantity is still 1 pending "
              "zip-bag-pack-quantity-400-vs-1.\n\nPLACED, not received."))
assert note_text(po).startswith("Auto-created"), "PO note did not stick"

for L, sp in zip(LINES, sps):
    li = PurchaseOrderLineItem(order=po, part=sp, quantity=L["qty"],
                               purchase_price=L["price"], purchase_price_currency="USD")
    li.save()
    li.refresh_from_db()
    assert float(li.quantity) == float(L["qty"]), li.quantity
    assert float(li.purchase_price.amount) == float(L["price"]), li.purchase_price
    print(f"  line: sp #{sp.pk} qty {li.quantity} @ {li.purchase_price}")
po.refresh_from_db()
print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
      f"target={po.target_date} lines={po.lines.count()}")
