"""Queue C, 12:40 daytime sweep 2026-10-30: one Amazon order -> one PO, one line.

  113-5067447-6100267  placed 2026-10-30, ship to The Villages FL (LRD), "Arriving tomorrow"
    1. Kamoer black NKP small peristaltic pump 12V DC ... 2mm ID x 4mm OD with BPT tube
                                        ASIN B092Z9HR3D   qty 1   $9.98

PRICE is the per-item price on the order-details page, read in Chrome 2026-10-30 12:4x.
Item subtotal $9.98, tax $0.70; grand total $0.00 because a $10.68 gift card was applied --
a payment method, not a discount, and not a price. The email said "Grand Total: 0.0 USD".

Dry run lists duplicate candidates (name/description/IPN/keywords/supplier SKU) and
categories. Pass --cat <pk> (or --part <pk> to reuse) and --commit to write. PLACED, never
received.
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

RUN = "12:40 daytime sweep 2026-10-30"
TODAY = datetime.date(2026, 10, 30)
ARRIVE = datetime.date(2026, 10, 31)

HITS = (Q(name__icontains="peristaltic") | Q(description__icontains="peristaltic")
        | Q(keywords__icontains="peristaltic") | Q(name__icontains="kamoer")
        | Q(description__icontains="kamoer") | Q(IPN__icontains="kamoer")
        | Q(description__icontains="B092Z9HR3D") | Q(link__icontains="B092Z9HR3D")
        | Q(name__icontains="dosing pump") | Q(name__icontains="pump"))
CATS = (Q(name__icontains="pump") | Q(name__icontains="fluid") | Q(name__icontains="motor")
        | Q(name__icontains="pneumatic") | Q(name__icontains="plumbing")
        | Q(name__icontains="coolant"))

L = dict(
    order="113-5067447-6100267",
    asin="B092Z9HR3D", qty=1, price="9.98",
    name="Peristaltic Pump, 12 V DC, 2 mm ID x 4 mm OD BPT tube - Kamoer NKP",
    desc=("orig: Kamoer black NKP small peristaltic pump 12V DC long service life liquid dosing "
          "pump for aquarium DIY lab analytical 2mm ID x 4mm OD with BPT tube"),
    kw=("peristaltic pump, dosing pump, liquid pump, fluid transfer, metering pump, 12V, 12 V DC, "
        "DC motor pump, Kamoer, NKP, BPT tube, 2mm ID, 4mm OD, aquarium, lab, coolant dosing"),
    sp_desc="Kamoer NKP peristaltic pump 12 V DC, 2x4 mm BPT tube",
    notes=("Kamoer NKP mini peristaltic (dosing) pump, 12 V DC brushed motor, black, "
           "BPT tube 2 mm ID x 4 mm OD. Sold singly (pack 1)."),
    po_desc=f"Amazon order 113-5067447-6100267 — Kamoer NKP 12 V peristaltic pump (to The Villages FL)",
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
sp = SupplierPart.objects.filter(supplier=amazon, SKU__iexact=L["asin"]).first()
if sp:
    print(f"  supplier part {L['asin']} already exists: sp #{sp.pk} -> part #{sp.part_id} "
          f"pack={sp.pack_quantity} native={sp.pack_quantity_native}")
for s in SupplierPart.objects.filter(Q(SKU__icontains="kamoer") | Q(description__icontains="peristaltic")
                                     | Q(description__icontains="kamoer")):
    print(f"  sp hit #{s.pk} {s.supplier.name} {s.SKU} -> part #{s.part_id} {s.part.name}")
for h in Part.objects.filter(HITS)[:40]:
    q = h.stock_items.aggregate(s=Sum("quantity"))["s"] or 0
    sps = [(s.supplier.name, s.SKU, s.pack_quantity) for s in h.supplier_parts.all()]
    print(f"  candidate part #{h.pk}: {h.name}  active={h.active}  stock={float(q):g}  "
          f"cat={h.category_id}: {h.category}  sps={sps}")
print("  categories:")
for c in PartCategory.objects.filter(CATS):
    print(f"    {c.pk}: {c.pathstring}  ({c.parts.count()} parts)")

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --cat <pk> (or --part <pk>) --commit")

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
                    link=f"https://www.amazon.com/dp/{L['asin']}",
                    component=True, purchaseable=True, assembly=False)
        part.save()
        part.refresh_from_db()
        assert part.name == L["name"] and part.category_id == cat.pk and part.keywords == L["kw"]
        note_set(part, L["notes"] + f"\n\nOrdered 2026-10-30 to The Villages FL (LRD), "
                       f"Amazon {L['order']}.\n\nCreated by the queue C daytime sweep, {RUN}.")
        assert note_text(part).startswith(L["notes"][:30]), "part note did not stick"
        print(f"CREATED part #{part.pk} {part.name}  cat={part.category.pathstring}")
    sp = SupplierPart(supplier=amazon, part=part, SKU=L["asin"],
                      link=f"https://www.amazon.com/dp/{L['asin']}", description=L["sp_desc"])
    sp.save()
    sp.refresh_from_db()
    assert sp.SKU == L["asin"] and sp.part_id == part.pk, "sp did not stick"
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
assert po.supplier_id == amazon.pk and po.supplier_reference == L["order"]
assert po.status == PurchaseOrderStatus.PLACED.value and po.reference != L["order"]
note_set(po, (f"Auto-created by the queue C daytime sweep, {RUN}.\n\n"
              "Ships to The Villages FL (LRD).\n\n"
              "Line price read from the Amazon order-details page: $9.98, tax $0.70. Grand "
              "total $0.00 because a $10.68 gift card was applied -- a payment method, not a "
              "discount, and not a price.\n\nPLACED, not received."))
assert note_text(po).startswith("Auto-created"), "PO note did not stick"

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
