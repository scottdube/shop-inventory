"""Queue C, 22:40 daytime sweep 2026-11-02: two Amazon orders -> two PLACED POs.

  order                 item                                   qty x pack  price  arrives
  113-6991881-7123426   TOWOT precision tweezers, 5-pc set     1 x 1       28.99  Tue 11-03
  113-8879085-9694659   Kimtech 34155 KIMWIPES, 286/box        1 x 1        7.61  Tue 11-03
                        Mifoci PCB cleaning brush, 10 pcs      1 x 10      20.99  Wed 11-04

Both placed 2026-11-02, ship to The Villages FL (LRD). Prices are the item lines on the
order-details pages read in Chrome 2026-11-02 22:4x. Order 2 also carried $2.86 of rewards
points and a -$0.63 Amazon discount at order level: the email Grand Total ($37.76) is NOT a
price, per the task rule.

SKIPPED: the third line of 113-8879085-9694659 (Amazon category Personal Care) -- skipped
(personal), not transcribed. 113-6427021-0080205 is apparel (already skipped 11-01).

The tweezer set is 5 DIFFERENT tips -> an assortment, ONE unit, pack 1 (not a multipack).
Kimwipes count in boxes (pack 1). The brushes are 10 identical pieces -> pack 10.

Dry run by default prints dupe candidates and categories; --commit writes. PLACED, never
received.
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

RUN = "22:40 daytime sweep 2026-11-02"
PLACED = datetime.date(2026, 11, 2)

ITEMS = {
    "tweezers": dict(
        name="Tweezers Set 5pc Precision Stainless Non-Magnetic",
        desc=("orig: TOWOT Precision Tweezers, 5 PCS Stainless Steel, Non-Magnetic, Heat "
              "Resistant, Curved, Jewelry, Electronics, Craft, Soldering, Experimental Work"),
        kw=("tweezers, precision tweezers, curved tweezers, stainless, non-magnetic, "
            "anti-magnetic, SMD, soldering, set, TOWOT"),
        notes=("Five-piece precision tweezer set, assorted tips including curved; stainless, "
               "non-magnetic. An assortment: stock counts SETS, pack 1."),
        sp_desc="TOWOT precision tweezers, 5-pc set", pack="1",
        terms=["tweez"], cat_terms=["tweez", "hand tool", "soldering"]),
    "kimwipes": dict(
        name="Kimwipes Delicate Task Wipers 34155 4.4x8.4in (box 286)",
        desc=("orig: Kimtech 34155 KIMWIPES, Delicate Task Wipers, 1-Ply, 4 2/5 x 8 2/5, "
              "286/Box"),
        kw=("kimwipes, kimtech, 34155, task wipers, lint free, wipes, optics, cleaning, "
            "consumable, Kimberly-Clark"),
        notes=("Kimtech 34155 single-ply delicate task wipers, 4.4 x 8.4 in, 286 per box. "
               "Stock counts BOXES."),
        sp_desc="Kimtech 34155 KIMWIPES 286/box", pack="1",
        terms=["kimwipe", "kimtech", "34155", "task wiper"], cat_terms=["clean", "consum", "wipe"]),
    "brush": dict(
        name="Brush PCB Cleaning Precision Fine Bristle",
        desc=("orig: Mifoci 10 Pcs Precision Pcb Cleaning Brush, with 10000 Soft Fine Bristles "
              "| with 10000 Bristles, Flux Cleaner for Circuit Boards, Keyboard, Electronics "
              "Devices Maintenance, Phones, Tablets"),
        kw=("brush, PCB brush, flux brush, cleaning brush, ESD, fine bristle, flux removal, "
            "electronics cleaning, Mifoci"),
        notes=("Precision fine-bristle brush for scrubbing flux off PCBs. Amazon listing sells 10 "
               "identical brushes -> pack_quantity 10; stock counts brushes."),
        sp_desc="Mifoci PCB cleaning brush, 10 pcs", pack="10",
        terms=["brush"], cat_terms=["clean", "brush", "consum"]),
}

ORDERS = [
    dict(order="113-6991881-7123426", arrive=datetime.date(2026, 11, 3),
         lines=[("tweezers", "B0", 1, "28.99")],
         money="item line $28.99, tax $2.03, grand total $31.02"),
    dict(order="113-8879085-9694659", arrive=datetime.date(2026, 11, 4),
         lines=[("kimwipes", "B0", 1, "7.61"), ("brush", "B0", 1, "20.99")],
         money=("item lines $7.61 (Kimwipes) and $20.99 (brushes); order also had a $9.99 line "
                "skipped (personal), a -$0.63 Amazon discount and $2.86 rewards points, so the "
                "$37.76 grand total is not a price")),
]

# Filled from the dry run. No reuse: #970 is McMaster's 4-piece set (a different product);
# #492 YCS motherboard brush (AliExpress, pack 5) is a different maker and bristle -- named in
# the new part's note so a merge stays a human call. Categories follow #970 and #492.
ASIN = {"tweezers": "B09J97YT3X", "kimwipes": "B07B7FJQVQ", "brush": "B0HF83M41L"}
REUSE = {"tweezers": None, "kimwipes": None, "brush": None}
CAT = {"tweezers": 41, "kimwipes": 56, "brush": 56}
ITEMS["brush"]["notes"] += " Similar: #492 YCS soft-bristle motherboard brush (AliExpress)."

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

for key, it in ITEMS.items():
    q = Q()
    for t in it["terms"]:
        q |= Q(name__icontains=t) | Q(description__icontains=t) | Q(keywords__icontains=t)
    print(f"\n[{key}] part candidates:")
    for c in Part.objects.filter(q)[:25]:
        sps = [(s.pk, s.supplier.name, s.SKU, str(s.pack_quantity)) for s in c.supplier_parts.all()]
        print(f"  #{c.pk} active={c.active} cat={c.category_id} {c.name!r} | {c.description[:70]!r} sp={sps}")
    cq = Q()
    for t in it["cat_terms"]:
        cq |= Q(name__icontains=t)
    print(f"[{key}] categories: " + "; ".join(f"{c.pk}={c.pathstring}" for c in PartCategory.objects.filter(cq)[:15]))

for o in ORDERS:
    dup = PurchaseOrder.objects.filter(Q(supplier_reference=o["order"]) | Q(reference=o["order"]))
    print(f"{o['order']}: existing={[(p.reference, p.lines.count()) for p in dup]}")

if not args.commit:
    raise SystemExit("\nDRY RUN -- fill ASIN/REUSE/CAT, add --commit")

assert all(ASIN.values()) and all(CAT.values()), "fill ASIN and CAT from the dry run"


def supplier_part(key):
    it, asin = ITEMS[key], ASIN[key]
    sp = SupplierPart.objects.filter(supplier=amazon, SKU__iexact=asin).first()
    if sp:
        print(f"REUSE sp #{sp.pk} {asin} -> part #{sp.part_id}")
        return sp
    part = Part.objects.get(pk=REUSE[key]) if REUSE[key] else Part.objects.filter(name__iexact=it["name"]).first()
    if part is None:
        part = Part(name=it["name"], description=it["desc"], keywords=it["kw"],
                    category=PartCategory.objects.get(pk=CAT[key]),
                    link=f"https://www.amazon.com/dp/{asin}",
                    component=True, purchaseable=True, assembly=False)
        part.save()
        part.refresh_from_db()
        assert part.name == it["name"] and part.keywords == it["kw"], "part did not stick"
        note_set(part, it["notes"] + f"\n\nCreated by the queue C daytime sweep, {RUN}.")
        assert note_text(part).startswith(it["notes"][:30]), "part note did not stick"
        print(f"CREATED part #{part.pk} {part.name}")
    else:
        print(f"REUSE part #{part.pk} {part.name}")
    sp = SupplierPart(supplier=amazon, part=part, SKU=asin,
                      link=f"https://www.amazon.com/dp/{asin}", description=it["sp_desc"])
    sp.pack_quantity = it["pack"]
    sp.save()  # .save(), never .update(): only pack_quantity_native is read at receive
    sp.refresh_from_db()
    assert sp.SKU == asin and sp.part_id == part.pk, "sp did not stick"
    assert float(sp.pack_quantity_native) == float(it["pack"]), sp.pack_quantity_native
    print(f"CREATED sp #{sp.pk} {asin} -> part #{part.pk} pack native={sp.pack_quantity_native}")
    return sp


for o in ORDERS:
    order = o["order"]
    dup = PurchaseOrder.objects.filter(Q(supplier_reference=order) | Q(reference=order))
    if dup.exists():
        assert dup.count() == 1
        po = dup.first()
        if po.lines.count():
            print(f"SKIP {order}: {po.reference} already has lines")
            continue
        print(f"RESUMING {po.reference} (0 lines)")
    else:
        what = ", ".join(ITEMS[k]["sp_desc"] for k, *_ in o["lines"])
        po = PurchaseOrder(supplier=amazon, reference=PurchaseOrder.generate_reference(),
                           supplier_reference=order,
                           description=f"Amazon order {order} — {what} (to The Villages FL)",
                           issue_date=PLACED, target_date=o["arrive"],
                           status=PurchaseOrderStatus.PLACED.value)
        po.save()
        po.refresh_from_db()
    assert po.supplier_id == amazon.pk and po.supplier_reference == order
    assert po.status == PurchaseOrderStatus.PLACED.value and po.reference != order
    packs = "; ".join(f"{ITEMS[k]['sp_desc']} pack {ITEMS[k]['pack']}" for k, *_ in o["lines"])
    note_set(po, f"Auto-created by the queue C daytime sweep, {RUN}.\n\nShips to The Villages FL (LRD).\n\n"
                 f"Prices read from the Amazon order-details page: {o['money']}.\n\n"
                 f"Supplier-part packs: {packs}.\n\nPLACED, not received.")
    assert note_text(po).startswith("Auto-created"), "PO note did not stick"
    for key, _, qty, price in o["lines"]:
        sp = supplier_part(key)
        li = PurchaseOrderLineItem(order=po, part=sp, quantity=qty,
                                   purchase_price=price, purchase_price_currency="USD")
        li.save()
        li.refresh_from_db()
        assert float(li.quantity) == qty and float(li.purchase_price.amount) == float(price)
    po.refresh_from_db()
    print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
          f"target={po.target_date} lines={po.lines.count()}")
