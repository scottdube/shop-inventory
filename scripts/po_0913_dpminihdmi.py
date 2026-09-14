"""Queue C: Amazon order 113-0032375-3000231 (2026-09-13) -> PO + 1 part.

One line: a DisplayPort to Mini-HDMI cable, 6.6 ft. Placed 17:45 EDT, i.e.
AFTER the 16:46 sweep ran, which is why the 22:40 run is the one that sees it.

PRICE SOURCE -- the order-details page, per item:

    ZeniKon DP -> Mini HDMI 6.6FT     12.99 x 1
                                      -----
                                      12.99

which reconciles exactly to the page's Item(s) Subtotal of $12.99 with
shipping $0.00 and tax $0.00. The Grand Total happens to equal the subtotal
on this order, but it is still not the price source: points and gift cards
apply invisibly under a grand total and have silently mispriced an order on
this install before.

PACK: 1. "6.6FT" is a LENGTH, not a multipack -- the same call made for the
50 ft speaker wire on PO-0171 earlier today.

DUPLICATE CHECK (probe_0913_2240.py, searched the requirement rather than
the chosen part number): 13 display-cable-shaped parts exist and NONE is a
DP-to-Mini-HDMI lead. The near misses and why each is a different part:
  * pk 265 QimKero Mini HDMI -> HDMI adapter -- an ADAPTER not a cable, and
    inactive (returned to vendor, a merge receipt not a live part)
  * pk 1181 / 1185 Monoprice MST hubs -- hubs, bought 2026-09-09/10
  * pk 1145 micro-HDMI pigtail -- micro (Type D), not mini (Type C)
Mini and micro HDMI are different connectors; conflating them is exactly the
kind of near-duplicate that has been entered twice here before.

CATEGORY: Electronics/Cables, following pk 1145 (the micro-HDMI adapter
pigtail) -- the closest precedent, and a cable. Modules was the alternative
and was rejected: the two Monoprice parts sit there because they are active
MST hubs with silicon in them, and this is a passive lead.

Resolved by pathstring, not by a hard-coded pk, so a category renumbering
fails loudly instead of filing the part somewhere wrong.

PLACED, never received. Arriving 2026-09-14; a human checks it in with
receive_po.py.
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

ORDER = "113-0032375-3000231"
ISSUE = datetime.date(2026, 9, 13)
ARRIVES = datetime.date(2026, 9, 14)
SUBTOTAL = 12.99

ASIN = "B0GZVWP2JF"
UNIT = "12.99"
QTY = 1
PACK = "1"

NAME = "Adapter Cable, DisplayPort male to Mini-HDMI male, 4K, 2 m (6.6 ft)"
ORIG = ("ZeniKon 4K Display Port to Mini HDMI Cable 6.6FT, DP to Mini HDMI "
        "Cable")
DESC = ("One-piece DisplayPort to Mini-HDMI (Type C) cable, 6.6 ft / ~2 m, "
        "4K capable. Source end DP, sink end mini-HDMI. orig: ")
KW = ("displayport to mini hdmi, DP to mini HDMI, mini HDMI, type C HDMI, "
      "display cable, video cable, adapter cable, 4K, 6.6ft, zenikon")
SPNOTE = ("Sold by ZeniKon via Amazon. 6.6FT is a length, not a multipack -- "
          "pack_quantity 1.")
PNOTE = (
    "DIRECTIONAL, and this is the thing to check before reaching for it: a "
    "passive DP-to-HDMI lead converts ONE WAY ONLY, DisplayPort source into "
    "an HDMI sink. It will not drive a DisplayPort monitor from an HDMI "
    "output, and there is nothing on the cable that says so.\n\n"
    "MINI-HDMI (Type C) at the sink end, NOT micro-HDMI (Type D). The shop "
    "also holds micro-HDMI leads (pk 1145, pk 255, pk 272) and the two "
    "connectors look alike at arm's length. Mini is the wider one.\n\n"
    "Bought the same week as the two Monoprice MST hubs (pk 1181, pk 1185) "
    "and the VSDISPLAY 12.6in 1920x515 strip panel. That co-purchase is an "
    "observation about timing, not a documented wiring plan -- ask before "
    "assuming it belongs to a particular display chain.\n\n"
    "NOT COUNTED. Ordered 2026-09-13, arriving 2026-09-14. No stock row "
    "exists and none should until the box is checked in.")

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

# ---------------------------------------------------------------- idempotency
dup_po = PurchaseOrder.objects.filter(
    Q(supplier_reference=ORDER) | Q(reference=ORDER))
if dup_po.exists():
    sys.exit(f"!! PO already exists for {ORDER}: "
             f"{[p.reference for p in dup_po]} — nothing to do")

total = float(UNIT) * QTY
print(f"reconcile: lines sum {total:.2f} vs page subtotal {SUBTOTAL:.2f}")
assert abs(total - SUBTOTAL) < 0.005, "line price does not reconcile — refusing"

cat = PartCategory.objects.get(pathstring="Electronics/Cables")
sp_hits = SupplierPart.objects.filter(supplier=amazon, SKU=ASIN)
pt_hits = Part.objects.filter(Q(name=NAME) | Q(description__icontains=ORIG[:40]))
print(f"  {ASIN}  sp={sp_hits.count()} part={pt_hits.count()}  "
      f"[{cat.pathstring}] qty {QTY} x ${UNIT} pack {PACK}")

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ---------------------------------------------------------------- PO
po = PurchaseOrder(
    supplier=amazon,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=f"Amazon order {ORDER} — DP to mini-HDMI cable",
    issue_date=ISSUE,
    target_date=ARRIVES,
    status=PurchaseOrderStatus.PLACED.value,
    notes=("Auto-created by the queue C daytime sweep, 22:40 run 2026-09-13. "
           "The order was placed at 17:45 EDT, after the 16:46 sweep, so this "
           "is the first run that could see it.\n\n"
           "PRICE SOURCE: the order-details page, per item — $12.99, which "
           "reconciles exactly to the page's Item(s) Subtotal with shipping "
           "$0.00 and tax $0.00. The Grand Total matches the subtotal on this "
           "order, but a grand total is never the price source here: points "
           "and gift cards apply invisibly under it.\n\n"
           "PLACED, not received. Arriving 2026-09-14; receive with "
           "receive_po.py when the box is physically checked in."),
)
po.save()
po.refresh_from_db()
assert po.status == PurchaseOrderStatus.PLACED.value, "PO status did not stick"
assert po.supplier_reference == ORDER, "supplier_reference did not stick"
print(f"\nCREATED {po.reference} supplier_ref={po.supplier_reference}")

part = pt_hits.first()
if part is None:
    part = Part.objects.create(
        name=NAME[:250],
        description=(DESC + ORIG)[:250],
        category=cat,
        purchaseable=True, component=False, active=True,
        keywords=KW[:250],
        link=f"https://www.amazon.com/dp/{ASIN}",
    )
    Part.objects.filter(pk=part.pk).update(notes=PNOTE)
    part.refresh_from_db()
    assert part.keywords and part.notes, f"part fields did not stick: {part.pk}"
    print(f"  CREATED part #{part.pk} {part.name}")
else:
    print(f"  REUSED  part #{part.pk} {part.name}")

sp = sp_hits.first()
if sp is None:
    sp = SupplierPart(supplier=amazon, part=part, SKU=ASIN,
                      link=f"https://www.amazon.com/dp/{ASIN}",
                      note=SPNOTE)
    sp.pack_quantity = PACK
    sp.save()  # .save() not .update(): only pack_quantity_native counts
    sp.refresh_from_db()
    assert float(sp.pack_quantity_native) == float(PACK), \
        f"pack native did not stick on {ASIN}"
    print(f"    sp #{sp.pk} pack_native={sp.pack_quantity_native}")
else:
    print(f"    sp #{sp.pk} reused")

li = PurchaseOrderLineItem(
    order=po, part=sp, quantity=QTY,
    purchase_price=UNIT, purchase_price_currency="USD",
    notes="Per-item price from the Amazon order-details page.")
li.save()
li.refresh_from_db()
assert float(li.purchase_price.amount) == float(UNIT), \
    f"price did not stick: {li.purchase_price}"
print(f"    line: qty {li.quantity} @ {li.purchase_price}")

po.refresh_from_db()
booked = sum(float(l.purchase_price.amount) * float(l.quantity)
             for l in po.lines.all())
print(f"\nDONE  {po.reference}  lines={po.lines.count()}  booked=${booked:.2f}"
      f"  (page subtotal ${SUBTOTAL:.2f})")
assert abs(booked - SUBTOTAL) < 0.005, "booked total drifted from the page"
