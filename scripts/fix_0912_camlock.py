"""Finish PO-0169 / part #1189 after po_0912_camlock.py aborted on a bad assert.

The abort was in the VERIFICATION, not the write: the line item's price came
back as Decimal('7.6900') and the assert compared it to the string '7.69'.
Everything up to and including the line item is on disk; only the queue-A image
step never ran. This re-verifies the whole chain numerically and attaches the
image. Idempotent -- safe to re-run.
"""
import argparse
import os
import sys
import urllib.request

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.core.files.base import ContentFile  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem  # noqa: E402

ORDER = "113-0958514-9540223"
ASIN = "B09QD4S7BN"
HIRES = ("https://m.media-amazon.com/images/W/BW_MEDIAX_AVIF_MEASUREMENT_1306696-T1"
         "/images/I/61ealOtrgVL._AC_SL1500_.jpg")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

po = PurchaseOrder.objects.get(supplier_reference=ORDER)
part = Part.objects.get(pk=1189)

print(f"{po.reference}  status={PurchaseOrderStatus(po.status).label}  "
      f"supplier={po.supplier.name}  issue={po.issue_date}")
for li in po.lines.all():
    print(f"  line: qty {li.quantity} @ {li.purchase_price} -> "
          f"part #{li.part.part.pk} {li.part.part.name}  (SKU {li.part.SKU}, "
          f"pack_native {li.part.pack_quantity_native})")
    assert float(li.purchase_price.amount) == 7.69, "price is wrong"
    assert float(li.part.pack_quantity_native) == 1.0, "pack native is wrong"
assert po.lines.count() == 1, "line count is wrong"
assert po.status == PurchaseOrderStatus.PLACED.value, "PO is not PLACED"
assert StockItem.objects.filter(part=part).count() == 0, \
    "stock exists — ordered is not received"
print(f"part #{part.pk} {part.name}")
print(f"  category={part.category.pathstring}  keywords={'Y' if part.keywords else 'n'}  "
      f"notes={'Y' if part.notes else 'n'}  image={'Y' if part.image else 'n'}")
print("chain verified: PO PLACED, 1 line @ $7.69, pack 1, no stock row")

if part.image:
    raise SystemExit("image already present — nothing to do")
if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit to fetch the image")

req = urllib.request.Request(HIRES, headers={
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36")})
with urllib.request.urlopen(req, timeout=30) as r:
    data = r.read()

# verify by CONTENT, never by status code: a defended host answers 200 text/html
if data[:3] != b"\xff\xd8\xff" or len(data) < 5000:
    raise SystemExit(f"REFUSED — {len(data)} bytes, magic {data[:4]!r} (not a JPEG)")

part.image.save(f"amazon_{ASIN}.jpg", ContentFile(data), save=True)
part.refresh_from_db()
assert part.image, "image did not stick"
print(f"image attached: {len(data)} bytes -> {part.image.name}")
