"""Scott asked 2026-11-14: one Amazon order -> one PLACED PO.

  order                 ASIN        qty x pack price  arrives
  113-3887127-0437007   B0922XTTNF  1 x  4    21.99  "Arriving tomorrow" (11-15)

Outus 12x12in clear CAST acrylic, 1/16in, 4-pack. Same listing as PO-0138 (SLN, 2026-08-24,
$16.99 then). Placed 2026-11-14, ships to The Villages FL (LRD): Scott wanted 1/16in at LRD and
the only stock is the 4 sheets at SLN L1-D3.

Price is the Item(s) Subtotal from the order-details page read in Chrome 2026-11-14: $21.99,
shipping $0, tax $1.54. Grand total $0.00 because gift card ($13.27) and Visa rewards ($10.26)
paid it -- the grand total is never an item price.

No Florida earmark: florida.py earmarks SLN stock to be carried south; this ships direct to LRD.

The supplier part (sp #689, pack 4) already exists; this script REQUIRES it and never creates a
part or a supplier part. Dry run by default; --commit writes. PLACED, never received.
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

from company.models import SupplierPart  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402
from plugins.notes_compat import note_set, note_text  # noqa: E402

ORDER = "113-3887127-0437007"
ASIN = "B0922XTTNF"
QTY, PRICE, PACK = 1, "21.99", 4
ISSUE = datetime.date(2026, 11, 14)
ARRIVE = datetime.date(2026, 11, 15)

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

sps = list(SupplierPart.objects.filter(SKU__iexact=ASIN, supplier__name__istartswith="Amazon"))
for s in sps:
    print(f"  sp #{s.pk} {s.SKU!r} supplier={s.supplier} -> part #{s.part_id} active={s.part.active} "
          f"{s.part.name!r} pack={s.pack_quantity_native}")
dup = PurchaseOrder.objects.filter(Q(supplier_reference=ORDER) | Q(reference=ORDER))
print(f"{ORDER}: existing={[p.reference for p in dup]}")

assert len(sps) == 1, f"expected one Amazon supplier part for {ASIN}, found {len(sps)}"
sp = sps[0]
assert sp.part_id == 1083 and sp.part.active, "not the active Outus 1/16in part"
assert float(sp.pack_quantity_native) == float(PACK)

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --commit")
if dup.exists():
    raise SystemExit(f"SKIP: {dup.first().reference} already exists for {ORDER}")

amazon = sp.supplier
po = PurchaseOrder(supplier=amazon, reference=PurchaseOrder.generate_reference(),
                   supplier_reference=ORDER,
                   description=f"Amazon order {ORDER} — Outus 1/16in clear cast acrylic 12x12, 4-pack (to The Villages FL)",
                   issue_date=ISSUE, target_date=ARRIVE,
                   status=PurchaseOrderStatus.PLACED.value)
po.save()
po.refresh_from_db()
assert po.reference != ORDER and po.status == PurchaseOrderStatus.PLACED.value
note_set(po, "Created 2026-11-14 at Scott's request.\n\nShips to The Villages FL (LRD).\n\n"
             "Line price is the Item(s) Subtotal from the Amazon order-details page: $21.99, "
             "shipping $0.00, tax $1.54. Grand total $0.00 (gift card $13.27 + Visa rewards $10.26).\n\n"
             f"Line is 1 pack of {PACK}; supplier part {ASIN} carries pack {PACK}, so receive_po.py "
             "books 4 sheets.\n\nSame listing as PO-0138 (SLN, 2026-08-24).\n\nPLACED, not received.")
assert note_text(po).startswith("Created"), "PO note did not stick"
li = PurchaseOrderLineItem(order=po, part=sp, quantity=QTY,
                           purchase_price=PRICE, purchase_price_currency="USD")
li.save()
li.refresh_from_db()
assert float(li.quantity) == QTY and float(li.purchase_price.amount) == float(PRICE)
po.refresh_from_db()
print(f"CREATED {po.reference} pk={po.pk} supplier_ref={po.supplier_reference} status={po.status} "
      f"target={po.target_date} lines={po.lines.count()}")
