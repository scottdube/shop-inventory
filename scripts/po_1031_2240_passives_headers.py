"""Queue C, 22:40 daytime sweep 2026-10-31: seven Amazon orders -> seven PLACED POs.

All placed 2026-10-31 evening ET, ship to The Villages FL (LRD). Prices are the per-item
prices on each order-details page, read in Chrome 2026-10-31 22:4x. Grand totals were mostly
$0.00-$7.48 because gift cards were applied; those are payment, not price.

  order                 ASIN        qty x pack price  arrives
  113-3396434-9597852   B008DS16PO  6 x  6.79          (no date shown, "Order received")
  113-1267183-4569824   B0GM7T6XWP  1 x  6.99          Wed 11-04
  113-3490102-5914621   B0GM7T6XWP  1 x  6.99          Thu 11-05
  113-1963651-2249843   B0GM7T6XWP  2 x  6.99          Thu 11-05
  113-0677667-6017021   B0CL9KXXZB  1 x  5.39          Mon 11-02
  113-1942682-2499416   B08BF91KY3  1 x  6.99          Mon 11-02
  113-5723051-9981849   B0CZ71WTV2  2 x  5.99          Fri 11-06

SKIPPED: 113-9633331-6297034 (5 x uxcell 20 pc 6x6x8 right-angle switch, $7.39) -- the order
page says Cancelled, not charged. 113-3396434 (6x6x9) looks like its replacement.

PART MAPPING (probe_1031_2240.py found NO Amazon supplier part for any of these ASINs):
  * B0GM7T6XWP 7-pin female header -> existing #1183 'Header Socket 1x7 Female 0.1in'. pack 60.
  * B08BF91KY3 1uF 50V MLCC 5.08mm -> existing #651 'Capacitor Ceramic 1uF'. pack 120.
  * B0CL9KXXZB 10k 5% 1/4W carbon film -> NEW part. Not #634 'Resistor 10k 1% 1/4W': a 5%
    part merged into a 1% row makes that row lie about tolerance. pack 100.
  * B008DS16PO right-angle 6x6x9 tact -> NEW part. Every existing 6x6 tact is top-actuated.
    Title reads "uxcell 2 Momentary..." but the bullets say "Package Content: 20 Pcs" and
    Number of Positions 20 -> pack 20.
  * B0CZ71WTV2 100uF 25V radial -> NEW part, deliberately sizeless. Three parts exist split by
    can size (#695 6x12, #686 6x7, #1423 5x11) and the listing states no size, so picking one
    would be a guess. Measure on receive; if it matches, move the supplier part to that part and
    deactivate this one (inactive = merge receipt). pack 20.

Packs are written through .save() so pack_quantity_native sticks. Lines are in packs at the
pack price. Rerunnable: an order whose PO already has lines is skipped; one with 0 lines
(a half-finished earlier commit) is resumed. Dry run by default; --commit writes.
PLACED, never received.
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

RUN = "22:40 daytime sweep 2026-10-31"
PLACED_ON = datetime.date(2026, 10, 31)
D = datetime.date

ITEMS = {
    "B0GM7T6XWP": dict(
        part=1183, pack="60",
        title="MTCELL 60 Pcs 7 Pin Female Header 2.54mm Single Row Straight Connector",
        sp_desc="MTCELL 1x7 female header 2.54mm straight, 60 pcs"),
    "B08BF91KY3": dict(
        part=651, pack="120",
        title="mxuteuk 120PCS 1uF 105 Multilayer Monolithic Ceramic Capacitor 5.08mm",
        sp_desc="mxuteuk 1uF 50V MLCC radial 5.08mm, 120 pcs"),
    "B0CL9KXXZB": dict(
        cat=69, pack="100",
        name="Resistor 10k 5% 1/4W carbon film",
        desc=("orig: Innfeeltech 100 Pcs 1/4W 5% Tolerance 10KΩ Carbon Film Resistor Resistance "
              "for DIY Project and Experiments"),
        kw=("resistor, 10k, 10 kohm, 10000 ohm, 103, 1/4W, 0.25W, 5%, carbon film, through hole, "
            "axial, THT, pull-up, Innfeeltech"),
        notes=("10 kΩ 5% 1/4 W carbon-film axial resistor. Kept apart from #634 (10k 1% 1/4W) "
               "because the tolerance differs. Amazon B0CL9KXXZB sells 100 -> pack_quantity 100."),
        title="Innfeeltech 100 Pcs 1/4W 5% 10KΩ Carbon Film Resistor",
        sp_desc="Innfeeltech 10k 5% 1/4W carbon film, 100 pcs"),
    "B008DS16PO": dict(
        cat=33, pack="20",
        name="Tactile Switch 6x6x9mm right angle, momentary",
        desc=("orig: uxcell 2 Momentary Right Angle Tactile Push Button Switch, 6 mm x 6 mm x 9 mm "
              "(listing: Package Content 20 Pcs)"),
        kw=("tactile switch, tact switch, push button, momentary, right angle, side actuated, "
            "6x6, 6mm, 6x6x9, through hole, PCB button, normally open, uxcell"),
        notes=("Right-angle (side-actuated) 6x6 mm tact switch, 9 mm body height, 3 mm button, "
               "through-hole, momentary NO. Every other 6x6 tact here is top-actuated. "
               "Amazon B008DS16PO: title says '2' but the listing bullets say 'Package Content: "
               "20 Pcs' -> pack_quantity 20. Verify the count on receive."),
        title="uxcell 20 pc Momentary Right Angle Tactile Push Button Switch, 6x6x9 mm",
        sp_desc="uxcell right-angle tact switch 6x6x9mm, 20 pcs"),
    "B0CZ71WTV2": dict(
        cat=51, pack="20",
        name="Capacitor Electrolytic 100uF 25V",
        desc=("orig: Tnisesm 20Pcs 100UF 25V Electrolytic Capacitor 100 UF MFD 25 Volt with "
              "Aluminum Radial Leads (part no. 100UF-25V-20PCS; can size not stated)"),
        kw=("capacitor, electrolytic, aluminum, 100uF, 100 uF, 25V, radial, through hole, "
            "105C, Tnisesm"),
        notes=("100 µF 25 V radial aluminum electrolytic, 105 °C, ±20%. The listing gives NO can "
               "size, and the existing 100uF 25V parts are split by size (#695 6x12, #686 6x7, "
               "#1423 5x11). Measure on receive: if it matches one, move the supplier part there "
               "and deactivate this part as a merge receipt. Amazon B0CZ71WTV2 sells 20 -> "
               "pack_quantity 20."),
        title="Tnisesm 20Pcs 100UF 25V Electrolytic Capacitor, radial",
        sp_desc="Tnisesm 100uF 25V radial electrolytic, 20 pcs"),
}

ORDERS = [
    dict(order="113-3396434-9597852", asin="B008DS16PO", qty=6, price="6.79", arrive=None,
         money="6 x $6.79 = subtotal $40.74, tax $2.88, gift card -$5.28, grand total $38.34",
         extra=("Looks like the replacement for 113-9633331-6297034 (5 x 20 pc 6x6x8 right-angle, "
                "$7.39), which the order page shows Cancelled. Page showed 'Order received', "
                "no arrival date.")),
    dict(order="113-1267183-4569824", asin="B0GM7T6XWP", qty=1, price="6.99", arrive=D(2026, 11, 4),
         money="$6.99, tax $0.49, gift card -$7.48, grand total $0.00", extra=None),
    dict(order="113-3490102-5914621", asin="B0GM7T6XWP", qty=1, price="6.99", arrive=D(2026, 11, 5),
         money="$6.99, tax $0.49, grand total $7.48", extra=None),
    dict(order="113-1963651-2249843", asin="B0GM7T6XWP", qty=2, price="6.99", arrive=D(2026, 11, 5),
         money="2 x $6.99 = subtotal $13.98, tax $0.98, gift card -$14.96, grand total $0.00",
         extra=None),
    dict(order="113-0677667-6017021", asin="B0CL9KXXZB", qty=1, price="5.39", arrive=D(2026, 11, 2),
         money="$5.39, tax $0.38, gift card -$4.29, grand total $1.48", extra=None),
    dict(order="113-1942682-2499416", asin="B08BF91KY3", qty=1, price="6.99", arrive=D(2026, 11, 2),
         money="$6.99, tax $0.49, grand total $7.48", extra=None),
    dict(order="113-5723051-9981849", asin="B0CZ71WTV2", qty=2, price="5.99", arrive=D(2026, 11, 6),
         money="2 x $5.99 = subtotal $11.98, tax $0.84, gift card -$12.82, grand total $0.00",
         extra="[measure can size on receive -- see the part note]"),
]
HEADER_ORDERS = [o["order"] for o in ORDERS if o["asin"] == "B0GM7T6XWP"]

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

for asin, it in ITEMS.items():
    for k in ("name", "desc", "kw"):
        if k in it:
            assert len(it[k]) <= {"name": 100, "desc": 250, "kw": 250}[k], (asin, k, len(it[k]))
    sp = SupplierPart.objects.filter(supplier=amazon, SKU__iexact=asin).first()
    if "part" in it:
        p = Part.objects.get(pk=it["part"])
        print(f"{asin}: REUSE part #{p.pk} {p.name!r} active={p.active} cat={p.category}\n"
              f"    desc={p.description!r}")
        assert p.active, f"part #{p.pk} inactive"
    else:
        dupe = Part.objects.filter(Q(name__iexact=it["name"]) | Q(description__icontains=asin))
        print(f"{asin}: NEW part {it['name']!r} in {PartCategory.objects.get(pk=it['cat']).pathstring}"
              f"  name/asin dupes={[d.pk for d in dupe]}")
    print(f"    existing Amazon sp: {sp.pk if sp else None}  pack {it['pack']}")

for o in ORDERS:
    dup = PurchaseOrder.objects.filter(Q(supplier_reference=o["order"]) | Q(reference=o["order"]))
    state = [(p.reference, p.lines.count()) for p in dup]
    print(f"{o['order']}: {o['qty']} x {o['asin']} @ {o['price']}  arrive={o['arrive']}  existing={state}")

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --commit")


def supplier_part(asin):
    it = ITEMS[asin]
    sp = SupplierPart.objects.filter(supplier=amazon, SKU__iexact=asin).first()
    if sp:
        return sp
    if "part" in it:
        part = Part.objects.get(pk=it["part"])
    else:
        part = Part.objects.filter(name__iexact=it["name"]).first()
        if part is None:
            part = Part(name=it["name"], description=it["desc"], keywords=it["kw"],
                        category=PartCategory.objects.get(pk=it["cat"]),
                        link=f"https://www.amazon.com/dp/{asin}",
                        component=True, purchaseable=True, assembly=False)
            part.save()
            part.refresh_from_db()
            assert part.name == it["name"] and part.keywords == it["kw"], "part did not stick"
            note_set(part, it["notes"] + f"\n\nCreated by the queue C daytime sweep, {RUN}.")
            assert note_text(part).startswith(it["notes"][:30]), "part note did not stick"
            print(f"CREATED part #{part.pk} {part.name}")
    sp = SupplierPart(supplier=amazon, part=part, SKU=asin,
                      link=f"https://www.amazon.com/dp/{asin}", description=it["sp_desc"])
    sp.pack_quantity = it["pack"]
    sp.save()  # .save(), never .update(): only pack_quantity_native is read at receive
    sp.refresh_from_db()
    assert sp.SKU == asin and sp.part_id == part.pk, "sp did not stick"
    assert float(sp.pack_quantity_native) == float(it["pack"]), \
        f"{asin} pack native {sp.pack_quantity_native} != {it['pack']}"
    print(f"CREATED sp #{sp.pk} {asin} -> part #{part.pk} pack native={sp.pack_quantity_native}")
    return sp


for o in ORDERS:
    it = ITEMS[o["asin"]]
    sp = supplier_part(o["asin"])
    dup = PurchaseOrder.objects.filter(Q(supplier_reference=o["order"]) | Q(reference=o["order"]))
    if dup.exists():
        assert dup.count() == 1, [p.reference for p in dup]
        po = dup.first()
        if po.lines.count():
            print(f"SKIP {o['order']}: {po.reference} already has lines")
            continue
        print(f"RESUMING {po.reference} (0 lines)")
    else:
        desc = f"Amazon order {o['order']} — {sp.description} x{o['qty']} (to The Villages FL)"
        if o["extra"] and o["extra"].startswith("["):
            desc += " " + o["extra"]
        po = PurchaseOrder(supplier=amazon, reference=PurchaseOrder.generate_reference(),
                           supplier_reference=o["order"], description=desc[:250],
                           issue_date=PLACED_ON, target_date=o["arrive"],
                           status=PurchaseOrderStatus.PLACED.value)
        po.save()
        po.refresh_from_db()
    assert po.supplier_id == amazon.pk and po.supplier_reference == o["order"]
    assert po.status == PurchaseOrderStatus.PLACED.value and po.reference != o["order"]
    note = (f"Auto-created by the queue C daytime sweep, {RUN}.\n\nShips to The Villages FL (LRD).\n\n"
            f"Line price read from the Amazon order-details page: {o['money']}. Gift card is a "
            f"payment method, not a discount, and not a price.\n\n"
            f"Line is in packs of {it['pack']} at the pack price; supplier part {o['asin']} carries "
            f"pack_quantity {it['pack']}, so receive_po.py books pieces.")
    if o["asin"] == "B0GM7T6XWP":
        note += (f"\n\nOne of THREE same-evening orders for this header: {', '.join(HEADER_ORDERS)} "
                 "(1 + 1 + 2 packs = 240 sockets). Imported as placed; flagged in case one was a "
                 "double checkout.")
    if o["extra"] and not o["extra"].startswith("["):
        note += "\n\n" + o["extra"]
    note += "\n\nPLACED, not received."
    note_set(po, note)
    assert note_text(po).startswith("Auto-created"), "PO note did not stick"
    li = PurchaseOrderLineItem(order=po, part=sp, quantity=o["qty"],
                               purchase_price=o["price"], purchase_price_currency="USD")
    li.save()
    li.refresh_from_db()
    assert float(li.quantity) == float(o["qty"]), li.quantity
    assert float(li.purchase_price.amount) == float(o["price"]), li.purchase_price
    po.refresh_from_db()
    print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
          f"target={po.target_date} lines={po.lines.count()} ({o['qty']} x sp #{sp.pk} @ {o['price']})")
