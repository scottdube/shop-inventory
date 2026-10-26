"""Queue C, 22:40 daytime sweep 2026-10-25: one eBay order -> one PO, one line.

  08-15346-93873  placed 2026-10-25, ship to The Villages FL (LRD), est. delivery Oct 29 - Nov 02
    1. Mitutoyo 293-349 digital micrometer, 0-1 in, 0.0001 in resolution
                     eBay item 257805225762  seller ballisticplayer  $91.00 x1

PRICE SOURCE -- the eBay order-confirmation email, itemised: "Price: $91.00".
  Subtotal $91.00, shipping $7.58, sales tax $6.90, total charged $105.48.
  The $105.48 is NOT a price.

SUPPLIER: eBay (Company #14), SKU = eBay item id, link = /itm/<item id> (po_1004_strobe.py
convention). One micrometer -> pack_quantity 1.

Dry run lists existing candidate parts and categories. Pass --cat <pk> (or --part <pk> to
reuse) and --commit to write. PLACED, never received.
"""
import argparse
import datetime
import os
import sys

import django
from django.db.models import Q, Sum

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from plugins.notes_compat import note_set, note_text  # noqa: E402

LI_HAS_NOTES = any(f.name == "notes" and f.concrete for f in PurchaseOrderLineItem._meta.get_fields())

RUN = "22:40 daytime sweep 2026-10-25"
TODAY = datetime.date(2026, 10, 25)
ARRIVE = datetime.date(2026, 11, 2)

HITS = (Q(name__icontains="micrometer") | Q(description__icontains="micrometer")
        | Q(keywords__icontains="micrometer") | Q(name__icontains="293-349")
        | Q(description__icontains="293-349") | Q(name__icontains="mitutoyo")
        | Q(description__icontains="mitutoyo"))
CATS = (Q(name__icontains="measur") | Q(name__icontains="metrolog") | Q(name__icontains="inspect")
        | Q(name__icontains="gauge") | Q(name__icontains="gage") | Q(name__icontains="micrometer"))

L = dict(
    order="08-15346-93873",
    item="257805225762", price="91.00", qty=1, pack="1", seller="ballisticplayer",
    subtotal="91.00", ship="7.58", tax="6.90", total="105.48",
    name="Micrometer, outside digital 0-1 in, 0.0001 in - Mitutoyo 293-349",
    desc="orig: Mitutoyo Digital Micrometer 0-1 in 0.0001 in Electronic Readout 293-349",
    kw=("micrometer, outside micrometer, digital micrometer, 0-1 in, 0.0001 in, electronic readout, "
        "Mitutoyo, 293-349, metrology, measuring, inspection"),
    notes=("Mitutoyo 293-349: digital outside micrometer, 0-1 in range, 0.0001 in resolution, "
           "electronic readout. Bought secondhand on eBay. One micrometer -> pack_quantity 1."),
    po_desc="eBay order 08-15346-93873 — Mitutoyo 293-349 digital micrometer 0-1 in (to The Villages FL)",
)

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--cat", type=int)
ap.add_argument("--part", type=int)
args = ap.parse_args()

ebay = Company.objects.get(name="eBay")
print(f"supplier: #{ebay.pk} {ebay.name}")

dup = PurchaseOrder.objects.filter(Q(supplier_reference=L["order"]) | Q(reference=L["order"]))
if dup.exists():
    sys.exit(f"!! PO already exists for {L['order']}: {[p.reference for p in dup]}")
assert len(L["kw"]) <= 250 and len(L["name"]) <= 100 and len(L["desc"]) <= 250, \
    (len(L["kw"]), len(L["name"]), len(L["desc"]))
print(f"--- {L['name']}")
sp = SupplierPart.objects.filter(supplier=ebay, SKU=L["item"]).first()
if sp:
    print(f"  supplier part {L['item']} already exists: sp #{sp.pk} -> part #{sp.part_id}")
for h in Part.objects.filter(HITS)[:40]:
    q = h.stock_items.aggregate(s=Sum("quantity"))["s"] or 0
    print(f"  candidate part #{h.pk}: {h.name}  active={h.active}  stock={float(q):g}  "
          f"cat={h.category_id}: {h.category}")
print("  categories:")
for c in PartCategory.objects.filter(CATS):
    print(f"    {c.pk}: {c.pathstring}  ({c.parts.count()} parts)")

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --cat <pk> (or --part <pk>) --commit")

sp = SupplierPart.objects.filter(supplier=ebay, SKU=L["item"]).first()
if sp:
    print(f"REUSING sp #{sp.pk} part #{sp.part_id}")
else:
    if args.part:
        part = Part.objects.get(pk=args.part)
        print(f"REUSING part #{part.pk} {part.name}")
    else:
        assert args.cat, "need --cat or --part"
        cat = PartCategory.objects.get(pk=args.cat)
        part = Part(name=L["name"], description=L["desc"], category=cat, keywords=L["kw"],
                    component=False, purchaseable=True, assembly=False)
        part.save()
        part.refresh_from_db()
        assert part.name == L["name"] and part.category_id == cat.pk and part.keywords == L["kw"]
        note_set(part, L["notes"] + f"\n\nOrdered 2026-10-25 to The Villages FL (LRD), "
                       f"eBay {L['order']}.\n\nCreated by the queue C daytime sweep, {RUN}.")
        assert note_text(part).startswith(L["notes"][:30]), "part note did not stick"
        print(f"CREATED part #{part.pk} {part.name}  cat={part.category.pathstring}")
    sp = SupplierPart(supplier=ebay, part=part, SKU=L["item"],
                      link=f"https://www.ebay.com/itm/{L['item']}",
                      description="Mitutoyo 293-349 digital micrometer 0-1 in (secondhand)")
    sp.pack_quantity = L["pack"]
    sp.save()
    sp.refresh_from_db()
    assert sp.SKU == L["item"] and sp.part_id == part.pk, "sp did not stick"
    assert float(sp.pack_quantity_native) == float(L["pack"]), \
        f"pack native {sp.pack_quantity_native} != {L['pack']}"
    print(f"  sp #{sp.pk}  pack_quantity={sp.pack_quantity} native={sp.pack_quantity_native}")

po = PurchaseOrder(
    supplier=ebay,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=L["order"],
    description=L["po_desc"],
    issue_date=TODAY, target_date=ARRIVE,
    status=PurchaseOrderStatus.PLACED.value,
)
po.save()
po.refresh_from_db()
assert po.status == PurchaseOrderStatus.PLACED.value
assert po.supplier_reference == L["order"] and po.reference != L["order"]
note_set(po, (f"Auto-created by the queue C daytime sweep, {RUN}.\n\n"
              "Ships to The Villages FL (LRD); eBay estimated delivery Thu Oct 29 - Mon Nov 02.\n\n"
              f"PRICE SOURCE: the eBay order-confirmation email, itemised — Price: ${L['price']} "
              f"x{L['qty']}. Subtotal ${L['subtotal']}, shipping ${L['ship']}, sales tax "
              f"${L['tax']}, total charged ${L['total']}.\n\n"
              f"Sold by the eBay seller {L['seller']}; supplier is eBay as the platform. "
              f"The ${L['total']} total is not a price and is deliberately not on the line.\n\n"
              "PLACED, not received."))
assert note_text(po).startswith("Auto-created"), "PO note did not stick"
li_note = (f"Per-item price from the eBay order confirmation (${L['price']}, seller "
           f"{L['seller']}), NOT the ${L['total']} total charged.")
li = PurchaseOrderLineItem(
    order=po, part=sp, quantity=L["qty"],
    purchase_price=L["price"], purchase_price_currency="USD")
if LI_HAS_NOTES:
    li.notes = li_note
li.save()
if not LI_HAS_NOTES:
    note_set(li, li_note)
li.refresh_from_db()
assert float(li.purchase_price.amount) == float(L["price"]), li.purchase_price
assert float(li.quantity) == float(L["qty"]), li.quantity
print(f"  line: sp #{sp.pk} qty {li.quantity} @ {li.purchase_price}")
po.refresh_from_db()
print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
      f"target={po.target_date} lines={po.lines.count()}")
