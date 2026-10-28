"""Queue C, 22:40 daytime sweep 2026-10-27: one Walmart order -> one PO, one line.

  2000155-68010813  placed 2026-10-27, ship to The Villages FL (LRD), "Arrives Wed, Oct 28"
    1. Sterilite Set of (10) 6 Quart Small Clear Plastic Storage Bins with Snap-On Lids, White
                                        Walmart item 5297809753   quantity 2 (two 10-packs)

WALMART PRICE SOURCE -- the order-details page, read in Chrome 2026-10-27 22:4x:
  Subtotal (2 items) $21.96, shipping $0 ("Normally $6.99, Now $0" -- the email's "You saved
  $6.99" is that waived delivery fee, not an item discount), taxes $1.54, total $23.50.
  No per-line price anywhere on the page or in the email.

PRICE LEFT NULL, tagged needs-price. The task file allows subtotal/qty only when the lines are
identical AND tax and shipping are both zero. Lines are identical and shipping is zero, but tax
is $1.54, so the condition is not met. $21.96 / 2 = $10.98 per 10-pack is recorded in the notes
as a CANDIDATE only; the rule question is on the decision queue (the subtotal is itemised
separately from tax here, so tax arguably cannot contaminate it -- that is Scott's call).

PACK: one line unit is a set of 10 bins, stock counts bins -> pack_quantity 10.

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

RUN = "22:40 daytime sweep 2026-10-27"
TODAY = datetime.date(2026, 10, 27)
ARRIVE = datetime.date(2026, 10, 28)

HITS = (Q(name__icontains="sterilite") | Q(description__icontains="sterilite")
        | Q(keywords__icontains="sterilite") | Q(name__icontains="6 quart")
        | Q(name__icontains="6 qt") | Q(description__icontains="5297809753")
        | Q(name__icontains="storage box") | Q(name__icontains="storage bin"))
CATS = (Q(name__icontains="storage") | Q(name__icontains="organi") | Q(name__icontains="bin")
        | Q(name__icontains="cabinet"))

L = dict(
    order="2000155-68010813",
    item="5297809753", qty=2, pack="10",
    subtotal="21.96", tax="1.54", total="23.50", candidate="10.98",
    name="Storage Box, 6 qt, clear w/ white snap lid - Sterilite",
    desc=("orig: Sterilite Set of (10) 6 Quart Small Clear Plastic Storage Bins with Snap-On Lids, "
          "White; Walmart item 5297809753"),
    kw=("storage box, storage bin, shoe box, clear bin, snap lid, lidded box, parts storage, "
        "organizer, Sterilite, 6 quart, 6 qt, clear, white lid, stackable"),
    sp_desc="Sterilite 6 qt clear storage box, white snap lid, set of 10",
    notes=("Sterilite 6 quart clear plastic storage box with white snap-on lid (shoe-box size). "
           "Stock counts single boxes; Walmart item 5297809753 sells a set of 10 -> "
           "pack_quantity 10 on the supplier part."),
    po_desc=("Walmart order 2000155-68010813 — Sterilite 6 qt clear storage boxes, 2 x set of 10 "
             "(to The Villages FL) [needs-price]"),
)

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--cat", type=int)
ap.add_argument("--part", type=int)
# 2026-10-27 22:4x: the first --commit saved the PO row, then the note write died on
# "database is locked". --resume finishes THAT PO (only if it still has no lines) instead of
# tripping the duplicate guard or creating a second one.
ap.add_argument("--resume", action="store_true")
args = ap.parse_args()

walmart = Company.objects.get(name="Walmart")

dup = PurchaseOrder.objects.filter(Q(supplier_reference=L["order"]) | Q(reference=L["order"])
                                   | Q(supplier_reference=L["order"].replace("-", "")))
RESUME = None
if dup.exists():
    if not args.resume:
        sys.exit(f"!! PO already exists for {L['order']}: {[p.reference for p in dup]}")
    assert dup.count() == 1, [p.reference for p in dup]
    RESUME = dup.first()
    assert RESUME.lines.count() == 0, f"{RESUME.reference} already has lines -- nothing to resume"
    print(f"RESUMING {RESUME.reference} (lines=0, status={RESUME.status})")
assert len(L["kw"]) <= 250 and len(L["name"]) <= 100 and len(L["desc"]) <= 250, \
    (len(L["kw"]), len(L["name"]), len(L["desc"]))
print(f"--- {L['name']}")
sp = SupplierPart.objects.filter(supplier=walmart, SKU__iexact=L["item"]).first()
if sp:
    print(f"  supplier part {L['item']} already exists: sp #{sp.pk} -> part #{sp.part_id} "
          f"pack={sp.pack_quantity} native={sp.pack_quantity_native}")
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

sp = SupplierPart.objects.filter(supplier=walmart, SKU__iexact=L["item"]).first()
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
                       f"Walmart {L['order']}.\n\nCreated by the queue C daytime sweep, {RUN}.")
        assert note_text(part).startswith(L["notes"][:30]), "part note did not stick"
        print(f"CREATED part #{part.pk} {part.name}  cat={part.category.pathstring}")
    sp = SupplierPart(supplier=walmart, part=part, SKU=L["item"],
                      link=f"https://www.walmart.com/ip/{L['item']}", description=L["sp_desc"])
    sp.pack_quantity = L["pack"]
    sp.save()
    sp.refresh_from_db()
    assert sp.SKU == L["item"] and sp.part_id == part.pk, "sp did not stick"
    assert float(sp.pack_quantity_native) == float(L["pack"]), \
        f"pack native {sp.pack_quantity_native} != {L['pack']}"
    print(f"  sp #{sp.pk}  pack_quantity={sp.pack_quantity} native={sp.pack_quantity_native}")

if RESUME:
    po = RESUME
else:
    po = PurchaseOrder(
        supplier=walmart,
        reference=PurchaseOrder.generate_reference(),
        supplier_reference=L["order"],
        description=L["po_desc"],
        issue_date=TODAY, target_date=ARRIVE,
        status=PurchaseOrderStatus.PLACED.value,
    )
    po.save()
    po.refresh_from_db()
assert po.supplier_id == walmart.pk and po.description == L["po_desc"], (po.supplier_id, po.description)
assert po.status == PurchaseOrderStatus.PLACED.value
assert po.supplier_reference == L["order"] and po.reference != L["order"]
note_set(po, (f"Auto-created by the queue C daytime sweep, {RUN}.\n\n"
              "Ships to The Villages FL (LRD).\n\n"
              "needs-price: the order-details page shows no line price, only "
              f"Subtotal (2 items) ${L['subtotal']}, shipping $0 (waived $6.99 delivery fee — the "
              f"email's 'you saved $6.99' is that fee, not an item discount), taxes ${L['tax']}, "
              f"total ${L['total']}.\n\n"
              f"CANDIDATE, NOT WRITTEN: ${L['subtotal']} / 2 = ${L['candidate']} per set of 10 "
              "(identical lines, zero shipping). Not written because the sweep's derived-price "
              f"rule also requires zero tax and tax is ${L['tax']}; ruling is on the decision "
              "queue.\n\nPLACED, not received."))
assert note_text(po).startswith("Auto-created"), "PO note did not stick"
li_note = (f"needs-price: no line price on the Walmart order page; candidate ${L['candidate']} per "
           f"set of 10 = subtotal ${L['subtotal']} / 2, held pending the derived-price ruling.")
li = PurchaseOrderLineItem(order=po, part=sp, quantity=L["qty"])
if LI_HAS_NOTES:
    li.notes = li_note
li.save()
if not LI_HAS_NOTES:
    note_set(li, li_note)
li.refresh_from_db()
assert li.purchase_price is None, li.purchase_price
assert float(li.quantity) == float(L["qty"]), li.quantity
print(f"  line: sp #{sp.pk} qty {li.quantity} @ {li.purchase_price}")
po.refresh_from_db()
print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
      f"target={po.target_date} lines={po.lines.count()}")
