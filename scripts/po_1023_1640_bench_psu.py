"""Queue C, 16:40 daytime sweep 2026-10-23: one Amazon order -> one PO, one line.

  113-1029803-6264250  placed 2026-10-23, ship to The Villages FL (LRD), "Arriving Sunday" (10-25)
    1. Jesverty SPS-3010V variable DC bench power supply, 0-32 V 0-10 A, switching
                                        B0DDPVDWPZ  sold by JIUYUAN GLOBAL  $49.99 x1

Confirmation email subject: "Ordered 1 item: Lab Equipment".

AMAZON PRICE SOURCE -- the order-details page, read in Chrome 2026-10-23 16:4x:
  Item(s) Subtotal $49.99, shipping $0.00, tax $3.50, Grand Total $53.49.  The $53.49 is NOT a price.

PACK: one supply -> pack_quantity 1.

Dry run lists existing candidate parts and categories. Pass --cat <pk> (or --part <pk> to
reuse) and --commit to write. PLACED, never received.
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

LI_HAS_NOTES = any(f.name == "notes" and f.concrete for f in PurchaseOrderLineItem._meta.get_fields())

RUN = "16:40 daytime sweep 2026-10-23"
TODAY = datetime.date(2026, 10, 23)
ARRIVE = datetime.date(2026, 10, 25)

HITS = (Q(name__icontains="bench power") | Q(name__icontains="bench supply")
        | Q(name__icontains="power supply, bench") | Q(name__icontains="lab power")
        | Q(name__icontains="jesverty") | Q(description__icontains="jesverty")
        | Q(name__icontains="SPS-30") | Q(description__icontains="SPS-30")
        | Q(name__icontains="variable dc") | Q(description__icontains="bench power supply"))
CATS = (Q(name__icontains="power") | Q(name__icontains="supply") | Q(name__icontains="supplies")
        | Q(name__icontains="test") | Q(name__icontains="bench") | Q(name__icontains="instrument")
        | Q(name__icontains="equipment"))

L = dict(
    order="113-1029803-6264250",
    asin="B0DDPVDWPZ", price="49.99", qty=1, pack="1", seller="JIUYUAN GLOBAL",
    subtotal="49.99", tax="3.50", total="53.49",
    name="Bench Power Supply, variable DC 0-32V 0-10A, switching - Jesverty SPS-3010V",
    desc=("orig: Jesverty DC Power Supply Variable, 0-32V 0-10A Switching Bench Power Supply with "
          "20W USB & Type-C Quick-Charge, Encoder Corase & Fine Adjustment Knob, Output Switch, "
          "4-Digit LED Display - SPS-3010V"),
    kw=("bench power supply, lab power supply, variable DC supply, DC power supply, adjustable, "
        "0-32V, 0-10A, 320W, switching, CV CC, Jesverty, SPS-3010V, USB-C, test equipment"),
    sp_desc="Jesverty SPS-3010V variable DC bench power supply 0-32V 0-10A",
    notes=("Jesverty SPS-3010V: switching variable DC bench supply, 0-32 V / 0-10 A, coarse+fine "
           "encoder knobs, output switch, 4-digit LED display, 20 W USB-A + USB-C quick-charge "
           "outputs. One supply -> pack_quantity 1."),
    po_desc="Amazon order 113-1029803-6264250 — Jesverty SPS-3010V bench power supply (to The Villages FL)",
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
    print(f"  supplier part {L['asin']} already exists: sp #{sp.pk} -> part #{sp.part_id}")
for h in Part.objects.filter(HITS | Q(description__icontains=L["asin"])
                             | Q(IPN__icontains=L["asin"][-6:]))[:40]:
    print(f"  candidate part #{h.pk}: {h.name}  active={h.active}  cat={h.category_id}: {h.category}")
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
        note_set(part, L["notes"] + f"\n\nOrdered 2026-10-23 to The Villages FL (LRD), "
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
              f"PRICE SOURCE: the order-details page — ${L['price']} each x{L['qty']}. "
              f"Item(s) Subtotal ${L['subtotal']}, shipping $0.00, tax ${L['tax']}, "
              f"Grand Total ${L['total']}.\n\n"
              f"The ${L['total']} grand total is not a price and is deliberately not on the "
              "line.\n\nPLACED, not received."))
assert note_text(po).startswith("Auto-created"), "PO note did not stick"
li_note = (f"Per-item price from the Amazon order-details page (${L['price']}, sold by "
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
