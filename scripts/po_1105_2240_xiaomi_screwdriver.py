"""Queue C, 22:40 daytime sweep 2026-11-05: one Amazon order -> one PLACED PO.

  order                 ASIN        qty x price  arrives
  113-1881178-4156235   B0CW3FSBVT  1 x 58.95    "Arriving tomorrow" (Fri 11-06)

Placed 2026-11-05, ships to The Villages FL (LRD). Price is the item line on the order-details
page read in Chrome 2026-11-05 22:4x: $58.95, tax $4.13, gift card -$5.28, rewards -$5.37,
grand total $52.43 (the email's Grand Total is NOT the price -- points and gift card applied).
Sold by HFC Lotus Inc. Single tool, pack 1.

Dry run (default) prints duplicate candidates and screwdriver/tool categories; the commit path
uses REUSE / CAT_PK set from that output.

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
from part.models import Part, PartCategory  # noqa: E402
from plugins.notes_compat import note_set, note_text  # noqa: E402

RUN = "22:40 daytime sweep 2026-11-05"
ORDER = "113-1881178-4156235"
ASIN = "B0CW3FSBVT"
QTY, PRICE, PACK = 1, "58.95", "1"
ISSUE = datetime.date(2026, 11, 5)
ARRIVE = datetime.date(2026, 11, 6)
NAME = "Xiaomi Electric Precision Screwdriver"
DESC = ("orig: Xiaomi Electric Precision Screwdriver, All-metal Gearbox, Powerful Magnetic Motor, "
        "Rechargeable Lithium Battery, S2 Steel Screwdriving Bits, Type-C Charging, Aluminium Alloy "
        "Case (Power Screwdriver)")
KW = ("electric screwdriver, precision screwdriver, power screwdriver, cordless, rechargeable, "
      "USB-C, S2 bits, electronics repair, Xiaomi, Mijia")
NOTES = ("Cordless electric precision screwdriver with S2 steel bit set in an aluminium case, "
         "USB-C rechargeable. Amazon B0CW3FSBVT, sold by HFC Lotus Inc. One tool, pack 1.")
SP_DESC = "Xiaomi electric precision screwdriver kit"
REUSE = None   # set from the dry run's candidate list; None = create NAME
CAT_PK = 40    # Equipment/Hand Tools, beside #1413 Wiha precision set; dry run found no dupe

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

cands = Part.objects.filter(
    Q(name__icontains="screwdriver") | Q(description__icontains="screwdriver")
    | Q(name__icontains="xiaomi") | Q(description__icontains="xiaomi")
    | Q(name__icontains="wowstick") | Q(description__icontains="wowstick")
    | Q(description__icontains=ASIN) | Q(IPN__icontains=ASIN))
for c in cands:
    print(f"  cand #{c.pk} active={c.active} cat={c.category_id} {c.name!r} | {c.description[:90]!r}")
sp_hits = SupplierPart.objects.filter(Q(SKU__iexact=ASIN) | Q(description__icontains="screwdriver"))
print(f"  sp hits: {[(s.pk, s.SKU, s.part_id) for s in sp_hits]}")
for cat in PartCategory.objects.filter(
        Q(name__icontains="screwdriver") | Q(name__icontains="hand tool")
        | Q(name__icontains="power tool") | Q(name__icontains="tools")):
    print(f"  category #{cat.pk} {cat.pathstring!r} parts={cat.parts.count()}")
dup = PurchaseOrder.objects.filter(Q(supplier_reference=ORDER) | Q(reference=ORDER))
print(f"{ORDER}: existing={[(p.reference, p.lines.count()) for p in dup]}")

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --commit")

sp = SupplierPart.objects.filter(supplier=amazon, SKU__iexact=ASIN).first()
if sp is None:
    part = Part.objects.get(pk=REUSE) if REUSE else Part.objects.filter(name__iexact=NAME).first()
    if part is None:
        assert CAT_PK, "set CAT_PK from the dry run"
        part = Part(name=NAME, description=DESC, keywords=KW,
                    category=PartCategory.objects.get(pk=CAT_PK),
                    link=f"https://www.amazon.com/dp/{ASIN}",
                    component=False, purchaseable=True, assembly=False)
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
             f"Line price read from the Amazon order-details page: $58.95, tax $4.13, gift card "
             f"-$5.28, rewards -$5.37, grand total $52.43.\n\nPLACED, not received.")
assert note_text(po).startswith("Auto-created"), "PO note did not stick"
li = PurchaseOrderLineItem(order=po, part=sp, quantity=QTY,
                           purchase_price=PRICE, purchase_price_currency="USD")
li.save()
li.refresh_from_db()
assert float(li.quantity) == QTY and float(li.purchase_price.amount) == float(PRICE)
po.refresh_from_db()
print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
      f"target={po.target_date} lines={po.lines.count()} ({QTY} x sp #{sp.pk} @ {PRICE})")
