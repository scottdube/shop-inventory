"""Queue C, 16:40 daytime sweep 2026-11-12: one AliExpress order -> one PLACED PO.

  order              seller                       qty x price  eta
  8216522373115753   QING WatchAccessories Store  10 x 1.73    2026-11-25

Placed and paid 2026-11-12, ships to The Villages FL (LRD). Everything below is verbatim from
aliexpress.com/p/order/detail.html?orderId=8216522373115753, read in Chrome 2026-11-12 16:4x:
item line "$1.73x10", variant "Diameter 35.5mm, Thick 2.0mm", Subtotal $17.30, Total $26.52.
The 9.22 between subtotal and total is shipping/tax and is NOT on the line (the ali_import.py
rule: item line, never Total/qty, which would read 2.652 = 53% high).

Not added to ali_import.py's ORDERS list because that script only attaches orders to parts
that already exist (part_pk); this one needs a new part, so it follows the Amazon one-order
script shape instead. Same Company #10, same order-number grain, same "<order>/<variant>" SKU.

What the crystals are FOR is not recorded anywhere this sweep can read, so the part says what
the listing says and nothing about a project.

Dry run (default) prints duplicate candidates and candidate categories; the commit path uses
REUSE / CAT_PK set from that output. PLACED, never received.
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
from plugins.notes_compat import note_set, note_text  # noqa: E402

RUN = "16:40 daytime sweep 2026-11-12"
ORDER = "8216522373115753"
SELLER = "QING WatchAccessories Store"
VARIANT = "Diameter 35.5mm, Thick 2.0mm"
SKU = f"{ORDER}/{VARIANT}"
QTY, PRICE, PACK = 10, "1.73", "1"
SUBTOTAL, TOTAL = "17.30", "26.52"
ISSUE = datetime.date(2026, 11, 12)
ARRIVE = datetime.date(2026, 11, 25)
NAME = "Watch Crystal, mineral glass, double dome, 35.5 mm dia x 2.0 mm"
DESC = ("orig: 1.0/1.5/2.0mm Thickness Watch Glass Replacement Double DomeMineral Watch Crystal "
        "28mm-38.5mm Transparent Watch Lens Repair Parts | variant: Diameter 35.5mm, Thick 2.0mm")
KW = ("watch crystal, watch glass, mineral glass, double dome, domed lens, round glass lens, "
      "35.5mm, 2mm thick, display cover, transparent")
NOTES = ("Round double-domed mineral-glass watch crystal, 35.5 mm diameter, 2.0 mm thick, clear. "
         "AliExpress order 8216522373115753, QING WatchAccessories Store, 10 pieces at $1.73. "
         "Sold singly, pack 1. Dimensions are the listing's, not measured.")
SP_DESC = "Watch crystal, double dome mineral glass, 35.5 mm x 2.0 mm (QING WatchAccessories Store)"
REUSE = None    # set from the dry run's candidate list; None = create NAME
CAT_PK = 136   # Hardware (83 parts). Dry run found no dupe and no optics/lens category;
                # rejected Displays (#25): it is a cover glass, not a display.

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

ali = Company.objects.get(pk=10)
print(f"supplier: #{ali.pk} {ali.name}")

cands = Part.objects.filter(
    Q(name__icontains="watch") | Q(description__icontains="watch glass")
    | Q(name__icontains="crystal") | Q(description__icontains="watch crystal")
    | Q(name__icontains="dome") | Q(description__icontains="double dome")
    | Q(keywords__icontains="watch") | Q(keywords__icontains="dome")
    | Q(name__icontains="35.5") | Q(description__icontains="35.5"))
for c in cands:
    print(f"  cand #{c.pk} active={c.active} cat={c.category_id} {c.name!r} | {c.description[:90]!r}")
sp_hits = SupplierPart.objects.filter(
    Q(SKU__icontains=ORDER) | Q(description__icontains="watch") | Q(description__icontains="dome"))
print(f"  sp hits: {[(s.pk, s.SKU, s.part_id) for s in sp_hits]}")
for cat in PartCategory.objects.filter(
        Q(name__icontains="lens") | Q(name__icontains="optic") | Q(name__icontains="glass")
        | Q(name__icontains="display") | Q(name__icontains="enclosure")
        | Q(name__icontains="material") | Q(name__icontains="mechanical")
        | Q(name__icontains="hardware") | Q(name__icontains="orb")):
    print(f"  category #{cat.pk} {cat.pathstring!r} parts={cat.parts.count()}")
dup = PurchaseOrder.objects.filter(Q(supplier_reference=ORDER) | Q(reference=ORDER))
print(f"{ORDER}: existing={[(p.reference, p.lines.count()) for p in dup]}")

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --commit")

sp = SupplierPart.objects.filter(supplier=ali, SKU__iexact=SKU).first()
if sp is None:
    part = Part.objects.get(pk=REUSE) if REUSE else Part.objects.filter(name__iexact=NAME).first()
    if part is None:
        assert CAT_PK, "set CAT_PK from the dry run"
        part = Part(name=NAME, description=DESC, keywords=KW,
                    category=PartCategory.objects.get(pk=CAT_PK),
                    component=True, purchaseable=True, assembly=False)
        part.save()
        part.refresh_from_db()
        assert part.name == NAME and part.keywords == KW, "part did not stick"
        note_set(part, NOTES + f"\n\nCreated by the queue C daytime sweep, {RUN}.")
        assert note_text(part).startswith(NOTES[:30]), "part note did not stick"
        print(f"CREATED part #{part.pk} {part.name}")
    else:
        print(f"REUSE part #{part.pk} {part.name}")
    sp = SupplierPart(supplier=ali, part=part, SKU=SKU, description=SP_DESC)
    sp.pack_quantity = PACK
    sp.save()  # .save(), never .update(): only pack_quantity_native is read at receive
    sp.refresh_from_db()
    assert sp.SKU == SKU and sp.part_id == part.pk, "sp did not stick"
    assert float(sp.pack_quantity_native) == float(PACK), sp.pack_quantity_native
    print(f"CREATED sp #{sp.pk} {SKU!r} -> part #{part.pk} pack native={sp.pack_quantity_native}")

if dup.exists():
    assert dup.count() == 1
    po = dup.first()
    if po.lines.count():
        raise SystemExit(f"SKIP {ORDER}: {po.reference} already has lines")
    print(f"RESUMING {po.reference} (0 lines)")
else:
    po = PurchaseOrder(supplier=ali, reference=PurchaseOrder.generate_reference(),
                       supplier_reference=ORDER,
                       description=f"AliExpress {ORDER} - {SELLER}"[:250],
                       issue_date=ISSUE, target_date=ARRIVE,
                       status=PurchaseOrderStatus.PLACED.value)
    po.save()
    po.refresh_from_db()
assert po.supplier_id == ali.pk and po.supplier_reference == ORDER
assert po.status == PurchaseOrderStatus.PLACED.value and po.reference != ORDER
note_set(po, f"AliExpress order {ORDER}. Seller: {SELLER}. Auto-created by the queue C daytime "
             f"sweep, {RUN}.\n\nShips to The Villages FL (LRD).\n\n"
             f"Item price {PRICE} x{QTY} read verbatim from the order-details page 2026-11-12. "
             f"Subtotal {SUBTOTAL}, order total {TOTAL} (includes 9.22 shipping/tax, NOT on the "
             f"line).\n\nItem: {DESC[6:]}\n\nPLACED, not received.")
assert note_text(po).startswith("AliExpress order"), "PO note did not stick"
li = PurchaseOrderLineItem(order=po, part=sp, quantity=QTY,
                           purchase_price=PRICE, purchase_price_currency="USD")
li.save()
li.refresh_from_db()
assert float(li.quantity) == QTY and float(li.purchase_price.amount) == float(PRICE)
po.refresh_from_db()
print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
      f"target={po.target_date} lines={po.lines.count()} ({QTY} x sp #{sp.pk} @ {PRICE})")
