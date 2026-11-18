"""Queue C, 16:40 daytime sweep 2026-11-18: one Amazon order -> one PLACED PO.

  order                 ASIN        qty x pack price  arrives
  113-1140909-0625040   B0BYSHVDDL  1 x  4    20.99  "Arriving tomorrow" (11-19)

KINLINK 12x12in clear cast acrylic, 1/8in (3 mm), 4-pack. Placed 2026-11-18, ships to The
Villages FL (LRD). Price is the item line / Item(s) Subtotal on the order-details page read in
Chrome 2026-11-18 16:4x: $20.99, shipping $0, tax $1.47, gift card -$3.79, rewards -$6.20,
grand total $12.47 -- the grand total is never an item price.

find_acrylic_1114.py (run this sweep) shows no 1/8in acrylic part: only #1083 (Outus 1/16in).
Thickness is identity, so this is a NEW part beside #1083, in #1083's category. "Cast" is the
seller's title, not confirmed by Scott (unlike #1083) -- the note says so.

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

RUN = "16:40 daytime sweep 2026-11-18"
ORDER = "113-1140909-0625040"
ASIN = "B0BYSHVDDL"
QTY, PRICE, PACK = 1, "20.99", "4"
ISSUE = datetime.date(2026, 11, 18)
ARRIVE = datetime.date(2026, 11, 19)
NAME = "Acrylic Sheet 12 x 12in, 1/8in thick, clear"
DESC = ("orig: KINLINK 12x12 3mm 1/8\" Clear Cast Acrylic Sheets Plastic Board 4 Pack | Plexiglass "
        "Sheets 1/8 inch Thick for DIY Project, Craft, Window Glass, Table Top, Acrylic Sign and "
        "Wedding Invitations")
KW = ("acrylic, PMMA, plexiglass, plexi, cast acrylic, clear, sheet, 1/8 in, 3 mm, 12x12, "
      "laser cutting, KINLINK")
NOTES = ("Clear acrylic sheet 12 x 12 in x 1/8 in (3 mm). Amazon B0BYSHVDDL, sold by kinlink, "
         "4-pack. 'Cast' is from the seller's title and NOT yet confirmed by Scott (the 1/16in "
         "Outus part #1083 was confirmed cast 2026-08-24). Cast lasers cleanly; extruded melts.")
SP_DESC = "KINLINK 1/8in clear cast acrylic 12x12, 4-pack"
SIBLING = 1083  # Outus 1/16in -- same category

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")
sib = Part.objects.get(pk=SIBLING)
print(f"sibling #{sib.pk} {sib.name!r} cat={sib.category_id} {sib.category.pathstring if sib.category else None!r}")

cands = Part.objects.filter(
    Q(name__icontains="acrylic") | Q(description__icontains="acrylic")
    | Q(name__icontains="kinlink") | Q(description__icontains="kinlink")
    | Q(description__icontains=ASIN) | Q(IPN__icontains=ASIN) | Q(IPN__icontains="acrylic"))
for c in cands:
    print(f"  cand #{c.pk} active={c.active} {c.name!r}")
sp_hits = SupplierPart.objects.filter(Q(SKU__iexact=ASIN) | Q(description__icontains="kinlink"))
print(f"  sp hits: {[(s.pk, s.SKU, s.part_id) for s in sp_hits]}")
dup = PurchaseOrder.objects.filter(Q(supplier_reference=ORDER) | Q(reference=ORDER))
print(f"{ORDER}: existing={[(p.reference, p.lines.count()) for p in dup]}")
assert not any("1/8" in c.name or "3 mm" in c.name or "3mm" in c.name for c in cands), "1/8 dupe?"

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --commit")

sp = SupplierPart.objects.filter(supplier=amazon, SKU__iexact=ASIN).first()
if sp is None:
    part = Part.objects.filter(name__iexact=NAME).first()
    if part is None:
        part = Part(name=NAME, description=DESC, keywords=KW, category=sib.category,
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
                       issue_date=ISSUE, target_date=ARRIVE,
                       status=PurchaseOrderStatus.PLACED.value)
    po.save()
    po.refresh_from_db()
assert po.supplier_id == amazon.pk and po.supplier_reference == ORDER
assert po.status == PurchaseOrderStatus.PLACED.value and po.reference != ORDER
note_set(po, f"Auto-created by the queue C daytime sweep, {RUN}.\n\nShips to The Villages FL (LRD).\n\n"
             "Line price is the item line from the Amazon order-details page: $20.99, shipping $0.00, "
             "tax $1.47, gift card -$3.79, rewards -$6.20, grand total $12.47.\n\n"
             f"Line is 1 pack of {PACK}; supplier part {ASIN} carries pack {PACK}, so receive_po.py "
             "books 4 sheets.\n\nPLACED, not received.")
assert note_text(po).startswith("Auto-created"), "PO note did not stick"
li = PurchaseOrderLineItem(order=po, part=sp, quantity=QTY,
                           purchase_price=PRICE, purchase_price_currency="USD")
li.save()
li.refresh_from_db()
assert float(li.quantity) == QTY and float(li.purchase_price.amount) == float(PRICE)
po.refresh_from_db()
print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
      f"target={po.target_date} lines={po.lines.count()} ({QTY} x sp #{sp.pk} @ {PRICE})")
