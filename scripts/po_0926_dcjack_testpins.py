"""Queue C, 22:40 sweep 2026-09-26: one Amazon order, two lines -> two new parts, ONE PO.

  113-0944289-3125861  placed 2026-09-26, "Arriving Monday" (2026-09-28)
    30PCS 5.5x2.1mm DC Power Jack, 2Pin Female Panel Mount   B0F7K8GVDF  WES SHOP  $6.29
    Comimark 100Pcs ... PCB Board Breadboard Test Point Pin   B07X32N4YJ  XieQianJin $6.49

PRICE SOURCE -- the order-details page, per item. Item(s) Subtotal $12.78,
shipping 0, tax 0, Grand Total $12.78 -- no rewards or gift card, so the email
total happens to agree, but it was not the source.

ASINs read off the product anchors whose text is the ordered item's title.

THE JACK IS A NEW PART, NOT A SECOND SUPPLIER PART ON #1261 -- and that was the
obvious alternative. Last night's PO-0182 created #1261 "DC Barrel Jack, 5.5 x
2.1 mm FEMALE, panel mount, 2-pin" from DIYhz B08CVCJ97Q, and tonight's title
reads the same. The two LISTINGS say different things:
    DIYhz  B08CVCJ97Q  24 V 4 A, M8 x 0.75 thread, hex nut, "5.5mm mounting hole"
    LEIFENY B0F7K8GVDF 24 V 3 A, 7.5-8 mm mounting hole, hex nut, 12 mm body,
                       9.5 mm socket depth, UL94 V2
Different makers and different current ratings; nothing establishes they are
the same body. Merging two supplier parts into one part later is a pk swap;
un-merging a combined stock row is a recount. So: separate part now, and a
decision to merge at check-in if the two are the same in the hand (thread,
body, pins). Name carries the rating and maker, the field marks that separate
it from #1261 today.

TEST POINTS: no existing test-point / test-pin part (probe_0926_2240.py; the
only hits were Tormach turret items). Listing: head 3.2 mm, fits 0.8-1.0 mm PCB
hole, 10 mm long, black insulator, gold-tone pin, Comimark model LY468. Filed in
flat `Prototyping` with the breadboard supply module (#844).

PACK written on both new supplier parts (30 and 100) through .save() so
pack_quantity_native follows -- leaving the default of 1 is the 688-of-706 bug.
The PO line is one pack at the pack price.

No image (02:05 job). No default_location. PLACED, never received.
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

ORDER = "113-0944289-3125861"
ISSUE = datetime.date(2026, 9, 26)
ARRIVES = datetime.date(2026, 9, 28)      # page: "Arriving Monday"
RUN = "22:40 run 2026-09-26"
SUBTOTAL = 12.78
GRAND = 12.78

LINES = [
    dict(
        asin="B0F7K8GVDF",
        seller="WES SHOP",
        unit="6.29", qty=1, pack="30",
        cat="Connectors",
        name="DC Barrel Jack, 5.5 x 2.1 mm FEMALE, panel mount, 2-pin, 3A (LEIFENY)",
        desc="orig: 30PCS 5.5x2.1mm DC Power Jack, 2Pin Female Panel Mount Socket Connector",
        keywords=("DC jack, DC power jack, barrel jack, barrel socket, 5.5x2.1, "
                  "5.5 x 2.1 mm, 2.1mm, panel mount, chassis mount, female, "
                  "DC socket, power input, 24V, 3A, hex nut, LEIFENY, DC-022"),
        notes=("Female 5.5 x 2.1 mm DC barrel socket for panel mounting, 2 pins, "
               "with hex nut. Listing (manufacturer LEIFENY): rated 3 A 24 V DC, "
               "mounting hole 7.5-8 mm, body 12 x 12 mm excluding pins, socket "
               "depth 9.5 mm, UL94 V2.\n\n"
               "POSSIBLY THE SAME PART AS #1261 (DIYhz B08CVCJ97Q, bought the day "
               "before) -- kept separate because the listings disagree on rating "
               "(4 A vs 3 A) and thread/hole, and nothing shows the bodies are "
               "identical. Compare the two in the hand at check-in; if thread, body "
               "and pins match, move this supplier part onto #1261 and retire this "
               "part (decision queue: dcjack-3a-vs-1261).\n\n"
               "NOT the same part as #1200 (the same socket on flying leads). "
               "'DC-022' keyword is a search aid, not an identity claim.\n\n"
               "Pack: 30 per Amazon unit (supplier fact, on the supplier part)."),
        po_desc="DC barrel jacks 5.5 x 2.1, panel mount (30-pack)",
    ),
    dict(
        asin="B07X32N4YJ",
        seller="XieQianJin",
        unit="6.49", qty=1, pack="100",
        cat="Prototyping",
        name="PCB Test Point Pin, black, 3.2 mm head, 0.8-1.0 mm hole",
        desc="orig: Comimark 100Pcs Black Gold Tone Soldering PCB Board Breadboard Test Point Pin",
        keywords=("test point, testpoint, test pin, PCB test pin, test hook point, "
                  "probe point, scope probe, solder-in, through hole, black, gold, "
                  "3.2mm head, 0.8mm, 1.0mm hole, 10mm, Comimark, LY468"),
        notes=("Solder-in PCB test point: black insulated head with a gold-tone "
               "pin, for clipping a scope probe or hook lead onto a board. "
               "Listing: head diameter 3.2 mm, fits a 0.8-1.0 mm PCB hole, total "
               "length 10 mm, ceramic/copper. Brand Comimark, model LY468.\n\n"
               "Only black was bought -- a colour is the whole point of a set of "
               "test points (GND vs signal), so if more colours arrive later they "
               "are separate parts, not a variant of this one.\n\n"
               "Pack: 100 per Amazon unit (supplier fact, on the supplier part)."),
        po_desc="PCB test point pins, black (100-pack)",
    ),
]

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

# ------------------------------------------------------------ checks, all rows
dup_po = PurchaseOrder.objects.filter(Q(supplier_reference=ORDER) | Q(reference=ORDER))
if dup_po.exists():
    sys.exit(f"!! PO already exists for {ORDER}: {[p.reference for p in dup_po]}")
total = 0.0
for o in LINES:
    print(f"\n=== {o['asin']}  {o['name']}")
    if SupplierPart.objects.filter(SKU__iexact=o["asin"]).exists():
        sys.exit(f"!! supplier part {o['asin']} already exists — resolve by hand")
    if Part.objects.filter(Q(IPN__iexact=o["asin"]) | Q(name=o["name"])).exists():
        sys.exit(f"!! a part with IPN {o['asin']} or this exact name exists")
    total += float(o["unit"]) * o["qty"]
    assert len(o["keywords"]) <= 250, f"keywords too long: {len(o['keywords'])}"
    assert len(o["name"]) <= 100, f"name too long: {len(o['name'])}"
    cats = [c for c in PartCategory.objects.filter(name=o["cat"].split("/")[-1])
            if c.pathstring == o["cat"]]
    assert len(cats) == 1, f"category {o['cat']} not unique: {cats}"
    o["cat_obj"] = cats[0]
    print(f"  category pk {cats[0].pk} {cats[0].pathstring} "
          f"({cats[0].parts.count()} parts)  pack {o['pack']}  "
          f"per piece ${float(o['unit']) / float(o['pack']):.4f}")
print(f"\nreconcile: lines {total:.2f} vs page subtotal {SUBTOTAL:.2f} "
      f"(grand total {GRAND:.2f})")
assert abs(total - SUBTOTAL) < 0.005, "lines do not reconcile — refusing"

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ------------------------------------------------------------------- writes
po = PurchaseOrder(
    supplier=amazon,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=f"Amazon order {ORDER} — " + "; ".join(o["po_desc"] for o in LINES),
    issue_date=ISSUE, target_date=ARRIVES,
    status=PurchaseOrderStatus.PLACED.value,
    notes=(f"Auto-created by the queue C daytime sweep, {RUN}.\n\n"
           "PRICE SOURCE: the order-details page, per item — $6.29 for one "
           "30-pack of DC jacks (sold by WES SHOP), $6.49 for one 100-pack of "
           "test points (sold by XieQianJin). Item(s) Subtotal $12.78, shipping "
           "$0.00, tax $0.00, Grand Total $12.78, no rewards or gift card.\n\n"
           "Both parts NEW; no duplicate by ASIN, IPN, name or description. The "
           "jack may prove to be the same part as #1261 — see its notes.\n\n"
           "PLACED, not received. Receive with receive_po.py when the box is "
           "physically checked in."),
)
po.save()
po.refresh_from_db()
assert po.status == PurchaseOrderStatus.PLACED.value, "PO status did not stick"
assert po.supplier_reference == ORDER, "supplier_reference did not stick"
assert po.reference != ORDER, "vendor number leaked into reference"
print(f"\nCREATED {po.reference} supplier_ref={po.supplier_reference}")

for o in LINES:
    part = Part(
        name=o["name"], description=o["desc"], category=o["cat_obj"],
        IPN=o["asin"], keywords=o["keywords"],
        component=True, purchaseable=True, assembly=False,
        notes=(o["notes"] + f"\n\nCreated by the queue C daytime sweep, {RUN}, "
               f"from Amazon order {ORDER} (sold by {o['seller']})."),
    )
    part.save()
    part.refresh_from_db()
    assert part.name == o["name"] and part.IPN == o["asin"], "part did not stick"
    assert part.category_id == o["cat_obj"].pk, "category did not stick"
    assert part.keywords == o["keywords"], "keywords did not stick"
    print(f"CREATED part #{part.pk} {part.name}  cat={part.category.pathstring}")

    sp = SupplierPart(supplier=amazon, part=part, SKU=o["asin"],
                      link=f"https://www.amazon.com/dp/{o['asin']}")
    sp.pack_quantity = o["pack"]      # .save() -> clean() -> pack_quantity_native
    sp.save()
    sp.refresh_from_db()
    assert float(sp.pack_quantity_native) == float(o["pack"]), \
        f"pack_quantity_native did not stick: {sp.pack_quantity_native}"
    print(f"  sp #{sp.pk} SKU={sp.SKU} pack={sp.pack_quantity} "
          f"native={sp.pack_quantity_native}")

    li = PurchaseOrderLineItem(
        order=po, part=sp, quantity=o["qty"],
        purchase_price=o["unit"], purchase_price_currency="USD",
        notes=f"Per-item price from the Amazon order-details page: one "
              f"{o['pack']}-pack at ${o['unit']}.")
    li.save()
    li.refresh_from_db()
    assert float(li.purchase_price.amount) == float(o["unit"]), \
        f"price did not stick: {li.purchase_price}"
    print(f"  line qty {li.quantity} @ {li.purchase_price}")

booked = sum(float(l.purchase_price.amount) * float(l.quantity) for l in po.lines.all())
assert po.lines.count() == len(LINES), "line count wrong"
assert abs(booked - SUBTOTAL) < 0.005, "booked total drifted from the page"
print(f"{po.reference}: {po.lines.count()} lines, booked ${booked:.2f}")
