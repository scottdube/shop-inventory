"""Queue C, 16:40 daytime sweep 2026-10-27: one Amazon order -> one PO, one line.

  113-2498939-4055456  placed 2026-10-27, ship to The Villages FL (LRD), "Arriving Thursday" (10-29)
    1. Akro-Mils 30220 AkroBins plastic storage bin, 7 x 4 x 3 in, red, 24-pack
                                        B000SMFFJQ  sold by Amazon.com  $38.66 x1 (one 24-pack)

AMAZON PRICE SOURCE -- the order-details page, read in Chrome 2026-10-27 16:4x:
  Item(s) Subtotal $38.66, shipping $0.00, tax $2.71, gift card -$26.81, rewards points
  -$14.56, Grand Total $0.00.  The email said "Grand Total: 0.0 USD" -- NOT a price.

PACK: the line is one 24-pack, and stock counts bins -> pack_quantity 24 (the multipack trap
in CLAUDE.md: the 19-bins-at-$208.62 mistake was exactly this item class).

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

RUN = "16:40 daytime sweep 2026-10-27"
TODAY = datetime.date(2026, 10, 27)
ARRIVE = datetime.date(2026, 10, 29)

HITS = (Q(name__icontains="akrobin") | Q(description__icontains="akrobin")
        | Q(name__icontains="30220") | Q(description__icontains="30220")
        | Q(keywords__icontains="akrobin") | Q(name__icontains="storage bin")
        | Q(name__icontains="akro"))
CATS = (Q(name__icontains="storage") | Q(name__icontains="organi") | Q(name__icontains="bin")
        | Q(name__icontains="cabinet"))

L = dict(
    order="113-2498939-4055456",
    asin="B000SMFFJQ", price="38.66", qty=1, pack="24", seller="Amazon.com",
    subtotal="38.66", tax="2.71", total="0.00",
    adj="gift card -$26.81, rewards points -$14.56, ",
    name="Storage Bin, stacking, 7x4x3 in, red - Akro-Mils 30220",
    desc=("orig: Akro-Mils 30220 AkroBins Plastic Storage Bins, 7\"x4\"x3\", Red, 24-Pack | "
          "Space-Saving Stackable Bins for Garage, Pantry, Craft Organization; Amazon B000SMFFJQ"),
    kw=("storage bin, stacking bin, hanging bin, louvered panel bin, parts bin, small parts storage, "
        "organizer, Akro-Mils, Akro, AkroBins, 30220, 7x4x3, red, bench storage"),
    sp_desc="Akro-Mils 30220 AkroBins 7x4x3 in, red, 24-pack",
    notes=("Akro-Mils 30220 AkroBins: stackable/hanging plastic storage bin, 7 in L x 4 in W x "
           "3 in H, red. Stock counts single bins; Amazon B000SMFFJQ sells a 24-pack -> "
           "pack_quantity 24 on the supplier part."),
    po_desc="Amazon order 113-2498939-4055456 — Akro-Mils 30220 AkroBins red, 24-pack (to The Villages FL)",
)

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--cat", type=int)
ap.add_argument("--part", type=int)
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

dup = PurchaseOrder.objects.filter(Q(supplier_reference=L["order"]) | Q(reference=L["order"]))
if dup.exists():
    sys.exit(f"!! PO already exists for {L['order']}: {[p.reference for p in dup]}")
assert len(L["kw"]) <= 250 and len(L["name"]) <= 100 and len(L["desc"]) <= 250, \
    (len(L["kw"]), len(L["name"]), len(L["desc"]))
print(f"--- {L['name']}")
sp = SupplierPart.objects.filter(SKU__iexact=L["asin"]).first()
if sp:
    print(f"  supplier part {L['asin']} already exists: sp #{sp.pk} -> part #{sp.part_id} "
          f"pack={sp.pack_quantity} native={sp.pack_quantity_native}")
for h in Part.objects.filter(HITS | Q(description__icontains=L["asin"]))[:40]:
    q = h.stock_items.aggregate(s=Sum("quantity"))["s"] or 0
    sps = [(s.supplier.name, s.SKU, s.pack_quantity) for s in h.supplier_parts.all()]
    print(f"  candidate part #{h.pk}: {h.name}  active={h.active}  stock={float(q):g}  "
          f"cat={h.category_id}: {h.category}  sps={sps}")
print("  categories:")
for c in PartCategory.objects.filter(CATS):
    print(f"    {c.pk}: {c.pathstring}  ({c.parts.count()} parts)")

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --cat <pk> (or --part <pk>) --commit")

sp = SupplierPart.objects.filter(SKU__iexact=L["asin"]).first()
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
        note_set(part, L["notes"] + f"\n\nOrdered 2026-10-27 to The Villages FL (LRD), "
                       f"Amazon {L['order']}.\n\nCreated by the queue C daytime sweep, {RUN}.")
        assert note_text(part).startswith(L["notes"][:30]), "part note did not stick"
        print(f"CREATED part #{part.pk} {part.name}  cat={part.category.pathstring}")
    sp = SupplierPart(supplier=amazon, part=part, SKU=L["asin"],
                      link=f"https://www.amazon.com/dp/{L['asin']}", description=L["sp_desc"])
    sp.pack_quantity = L["pack"]
    sp.save()
    sp.refresh_from_db()
    assert sp.SKU == L["asin"] and sp.part_id == part.pk, "sp did not stick"
    assert float(sp.pack_quantity_native) == float(L["pack"]), \
        f"pack native {sp.pack_quantity_native} != {L['pack']}"
    print(f"  sp #{sp.pk}  pack_quantity={sp.pack_quantity} native={sp.pack_quantity_native}")

po = PurchaseOrder(
    supplier=amazon,
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
              "Ships to The Villages FL (LRD).\n\n"
              f"PRICE SOURCE: the order-details page — ${L['price']} per 24-pack x{L['qty']}. "
              f"Item(s) Subtotal ${L['subtotal']}, shipping $0.00, tax ${L['tax']}, "
              f"{L['adj']}Grand Total ${L['total']}.\n\n"
              f"The ${L['total']} grand total (paid by gift card + points) is not a price and is "
              "deliberately not on the line.\n\nPLACED, not received."))
assert note_text(po).startswith("Auto-created"), "PO note did not stick"
li_note = (f"Per-pack price from the Amazon order-details page (${L['price']} per 24-pack, sold by "
           f"{L['seller']}), NOT the ${L['total']} grand total.")
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
