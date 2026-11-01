"""Queue C, 16:40 daytime sweep 2026-11-01: one Amazon order -> one PLACED PO.

  order                 ASIN        qty x pack price  arrives
  113-8305471-8507431   B0CZ6X313F  1 x  5.99          "Arriving tomorrow" (Mon 11-02)

Placed 2026-11-01, ships to The Villages FL (LRD). Price is the item line on the order-details
page read in Chrome 2026-11-01 16:4x: $5.99, tax $0.42, grand total $6.41.

Listing bullets: 40-pin 2.54 mm single-row straight female socket strip, "Total quantity:
20PCS" -> pack 20, counted in strips. Part mapping is decided by the dry run's dupe probe:
reuse an active 1x40 female header if exactly one exists, else create one in the category of
#1183 'Header Socket 1x7 Female 0.1in'.

SKIPPED this run: 113-6427021-0080205 (apparel), 113-9633331-6297034 (Cancelled on the order
page; already noted by the 10-31 22:40 import).

Dry run by default; --commit writes. PLACED, never received.
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

RUN = "16:40 daytime sweep 2026-11-01"
ORDER = "113-8305471-8507431"
ASIN = "B0CZ6X313F"
QTY, PRICE, PACK = 1, "5.99", "20"
ARRIVE = datetime.date(2026, 11, 2)
NAME = "Header Socket 1x40 Female 0.1in"
DESC = ("orig: Ferwooh 20PCS Single Row Straight Female Pin Socket Pin Header Connector Pin Strip "
        "2.54mm Spacing for PCB Board Shield (40 pins per strip)")
KW = ("female header, header socket, pin socket, 1x40, 40 pin, 2.54mm, 0.1in, single row, "
      "straight, breakaway, cuttable, through hole, Ferwooh")
NOTES = ("1x40 single-row straight female socket strip, 2.54 mm pitch, 101 x 11 x 2 mm, cuttable "
         "to length. Amazon B0CZ6X313F sells 20 strips -> pack_quantity 20; stock counts strips.")
SP_DESC = "Ferwooh 1x40 female header 2.54mm straight, 20 pcs"

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")
ref = Part.objects.get(pk=1183)
print(f"ref #1183 {ref.name!r} cat={ref.category_id} {ref.category}")

cands = Part.objects.filter(
    (Q(name__icontains="1x40") | Q(description__icontains="1x40") | Q(name__icontains="40 pin")
     | Q(description__icontains="40 pin") | Q(name__icontains="40P") | Q(description__icontains=ASIN)
     | Q(name__icontains="40-pin") | Q(description__icontains="40-pin")
     | Q(name__icontains="1 x 40") | Q(description__icontains="1 x 40")
     | Q(name__icontains="single row") | Q(description__icontains="single row")
     | Q(name__icontains="Header Socket 1x"))
    & (Q(name__icontains="female") | Q(description__icontains="female")
       | Q(name__icontains="socket") | Q(description__icontains="socket")))
for c in cands:
    print(f"  cand #{c.pk} active={c.active} {c.name!r} | {c.description[:90]!r}")
sp_hits = SupplierPart.objects.filter(SKU__iexact=ASIN)
print(f"  sp with SKU {ASIN}: {[(s.pk, s.part_id) for s in sp_hits]}")
dup = PurchaseOrder.objects.filter(Q(supplier_reference=ORDER) | Q(reference=ORDER))
print(f"{ORDER}: existing={[(p.reference, p.lines.count()) for p in dup]}")
REUSE = None  # set from the dry run's candidate list; None = create NAME

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --commit")

sp = SupplierPart.objects.filter(supplier=amazon, SKU__iexact=ASIN).first()
if sp is None:
    part = Part.objects.get(pk=REUSE) if REUSE else Part.objects.filter(name__iexact=NAME).first()
    if part is None:
        part = Part(name=NAME, description=DESC, keywords=KW, category=ref.category,
                    link=f"https://www.amazon.com/dp/{ASIN}",
                    component=True, purchaseable=True, assembly=False)
        part.save()
        part.refresh_from_db()
        assert part.name == NAME and part.keywords == KW, "part did not stick"
        note_set(part, NOTES + f"\n\nCreated by the queue C daytime sweep, {RUN}.")
        assert note_text(part).startswith(NOTES[:30]), "part note did not stick"
        print(f"CREATED part #{part.pk} {part.name}")
    else:
        print(f"REUSE part #{part.pk} {part.name}")
    sp = SupplierPart(supplier=amazon, part=part, SKU=ASIN,
                      link=f"https://www.amazon.com/dp/{ASIN}", description=SP_DESC)
    sp.pack_quantity = PACK
    sp.save()  # .save(), never .update(): only pack_quantity_native is read at receive
    sp.refresh_from_db()
    assert sp.SKU == ASIN and sp.part_id == part.pk, "sp did not stick"
    assert float(sp.pack_quantity_native) == float(PACK), sp.pack_quantity_native
    print(f"CREATED sp #{sp.pk} {ASIN} -> part #{part.pk} pack native={sp.pack_quantity_native}")

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
                       issue_date=datetime.date(2026, 11, 1), target_date=ARRIVE,
                       status=PurchaseOrderStatus.PLACED.value)
    po.save()
    po.refresh_from_db()
assert po.supplier_id == amazon.pk and po.supplier_reference == ORDER
assert po.status == PurchaseOrderStatus.PLACED.value and po.reference != ORDER
note_set(po, f"Auto-created by the queue C daytime sweep, {RUN}.\n\nShips to The Villages FL (LRD).\n\n"
             f"Line price read from the Amazon order-details page: $5.99, tax $0.42, grand total "
             f"$6.41.\n\nLine is in packs of {PACK} at the pack price; supplier part {ASIN} carries "
             f"pack_quantity {PACK}, so receive_po.py books strips.\n\nPLACED, not received.")
assert note_text(po).startswith("Auto-created"), "PO note did not stick"
li = PurchaseOrderLineItem(order=po, part=sp, quantity=QTY,
                           purchase_price=PRICE, purchase_price_currency="USD")
li.save()
li.refresh_from_db()
assert float(li.quantity) == QTY and float(li.purchase_price.amount) == float(PRICE)
po.refresh_from_db()
print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
      f"target={po.target_date} lines={po.lines.count()} ({QTY} x sp #{sp.pk} @ {PRICE})")
