"""Queue C, 16:40 daytime sweep 2026-11-11: one Amazon order -> one PLACED PO.

  order                 ASIN        qty x pack price  arrives
  113-3911830-6571465   B0GZ2KMYMZ  5 x  6    25.99  "Arriving Friday" (11-13)

Placed 2026-11-11, ships to The Villages FL (LRD). Price is the item line on the order-details
page read in Chrome 2026-11-11 16:4x: 5 x $25.99, subtotal $129.95, shipping $0, tax $9.10,
grand total $139.05. Sold by Aceirmc US. Listing: "6pcs 1.28 Inch 1.28'' TFT LCD Display Module
Round RGB 240 * 240 GC9A01 Driver 4 Wire SPI Interface 240x240 PCB for Arduino Nano STM32"
-> pack 6, counted in displays. Info Orbs display stock (5 x 6 = 30 displays).

Part mapping: an existing GC9A01 1.28in round display part is the expected reuse; the dry run
prints every candidate and its supplier parts, and --reuse <pk> picks one.

Dry run by default; --commit --reuse <pk> writes. PLACED, never received.
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
from plugins.notes_compat import note_set, note_text  # noqa: E402

RUN = "16:40 daytime sweep 2026-11-11"
ORDER = "113-3911830-6571465"
ASIN = "B0GZ2KMYMZ"
QTY, PRICE, PACK = 5, "25.99", "6"
ISSUE = datetime.date(2026, 11, 11)
ARRIVE = datetime.date(2026, 11, 13)
SP_DESC = "Aceirmc 1.28in round TFT GC9A01 240x240 SPI display module, 6 pcs"

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--reuse", type=int)
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

cands = Part.objects.filter(
    Q(name__icontains="GC9A01") | Q(description__icontains="GC9A01")
    | Q(name__icontains="1.28") | Q(description__icontains="1.28 inch")
    | Q(description__icontains=ASIN) | Q(IPN__icontains=ASIN) | Q(description__icontains="Aceirmc"))
for c in cands.order_by("pk"):
    print(f"  cand #{c.pk} active={c.active} {c.name!r} | {(c.description or '')[:90]!r}")
    for s in SupplierPart.objects.filter(part=c):
        print(f"      sp #{s.pk} {s.supplier} {s.SKU!r} pack={s.pack_quantity}/{s.pack_quantity_native}")
sp_hits = SupplierPart.objects.filter(SKU__iexact=ASIN)
print(f"  sp with SKU {ASIN}: {[(s.pk, s.part_id) for s in sp_hits]}")
dup = PurchaseOrder.objects.filter(Q(supplier_reference=ORDER) | Q(reference=ORDER))
print(f"{ORDER}: existing={[(p.reference, p.lines.count()) for p in dup]}")

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --commit --reuse <pk>")

assert args.reuse, "--reuse required"
ref = Part.objects.get(pk=args.reuse)
assert ref.active and "GC9A01" in (ref.name + (ref.description or "")), "reuse target is not a GC9A01 part"
print(f"REUSE #{ref.pk} {ref.name!r}")

sp = SupplierPart.objects.filter(supplier=amazon, SKU__iexact=ASIN).first()
if sp is None:
    sp = SupplierPart(supplier=amazon, part=ref, SKU=ASIN,
                      link=f"https://www.amazon.com/dp/{ASIN}", description=SP_DESC)
    sp.pack_quantity = PACK
    sp.save()  # .save(), never .update(): only pack_quantity_native is read at receive
    sp.refresh_from_db()
    assert sp.SKU == ASIN and sp.part_id == ref.pk, "sp did not stick"
    assert float(sp.pack_quantity_native) == float(PACK), sp.pack_quantity_native
    print(f"CREATED sp #{sp.pk} {ASIN} -> part #{ref.pk} pack native={sp.pack_quantity_native}")
else:
    assert sp.part_id == ref.pk, f"sp #{sp.pk} points at part #{sp.part_id}, not #{ref.pk}"

if dup.exists():
    assert dup.count() == 1
    po = dup.first()
    if po.lines.count():
        raise SystemExit(f"SKIP {ORDER}: {po.reference} already has lines")
    print(f"RESUMING {po.reference} (0 lines)")
else:
    po = PurchaseOrder(supplier=amazon, reference=PurchaseOrder.generate_reference(),
                       supplier_reference=ORDER,
                       description=f"Amazon order {ORDER} — {SP_DESC} x{QTY} (to The Villages FL)",
                       issue_date=ISSUE, target_date=ARRIVE,
                       status=PurchaseOrderStatus.PLACED.value)
    po.save()
    po.refresh_from_db()
assert po.supplier_id == amazon.pk and po.supplier_reference == ORDER
assert po.status == PurchaseOrderStatus.PLACED.value and po.reference != ORDER
note_set(po, f"Auto-created by the queue C daytime sweep, {RUN}.\n\nShips to The Villages FL (LRD).\n\n"
             f"Line price read from the Amazon order-details page: 5 x $25.99, subtotal $129.95, "
             f"shipping $0.00, tax $9.10, grand total $139.05.\n\nLine is in packs of {PACK} at the pack "
             f"price; supplier part {ASIN} carries pack_quantity {PACK}, so receive_po.py books "
             f"30 displays.\n\nPLACED, not received.")
assert note_text(po).startswith("Auto-created"), "PO note did not stick"
li = PurchaseOrderLineItem(order=po, part=sp, quantity=QTY,
                           purchase_price=PRICE, purchase_price_currency="USD")
li.save()
li.refresh_from_db()
assert float(li.quantity) == QTY and float(li.purchase_price.amount) == float(PRICE)
po.refresh_from_db()
print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
      f"target={po.target_date} lines={po.lines.count()} ({QTY} x sp #{sp.pk} @ {PRICE})")
