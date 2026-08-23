"""Clear the unreceived-PO backlog: 2026-08-23.

Twelve POs carried unreceived lines. They are NOT one problem, and receiving
them all the same way would have written stock that already exists. Three
classes, handled differently:

  A. NEW GOODS — nothing on the books. Straight receive into a real location.
     Scott confirmed in hand 2026-08-23: FNIRSI tester, SHT31-D x4, Avery
     sheets. The QL-810W is included because it is the printer that has been
     producing this shop's labels all week.

  B. ALREADY ON THE BOOKS — PO-0016's five MBR60100PT diodes were counted in
     hand 2026-08-19 and written as stock rows tagged to PO-0016, but the LINE
     never had `received` set. Calling receive_line_item would have written a
     SECOND five and reported ten. Fixed as bookkeeping only: `received` is set
     on the line, no stock is created. (It also could not be received anyway —
     receive_line_item raises unless the order is PLACED, and PO-0016 is
     Complete.)

  C. HISTORICAL (Tormach 2024 x2, MSC 2022) — eight of these parts already
     carried `[CONFIRMED OWNED — NOT COUNTED]` placeholder rows at qty 1 with
     no PO link, created 2026-08-19 from purchase history. Receiving on top of
     those would double them. Scott's call 2026-08-23: receive into the real
     locations and DELETE the placeholders, so stock carries purchase price and
     PO provenance instead of a bare assumption.

     **The received quantity is the PURCHASED quantity, not a count.** Three
     end-mill holders were ordered 2 each and the placeholders assumed 1 each.
     Neither figure was ever verified. The new rows get no stocktake_date and
     say so in their notes; the machine-shop walk settles it.

NOT touched, and deliberately: PO-0020 (fiberglass sleeve, in transit, ETA
Aug 25 - Sep 3), PO-0133 (DK-2205 roll, Scott says not arrived), PO-0029 (PET
sheet, returned — Returned with nothing received is the correct resting state),
TO-ORDER (a draft standing list, not a real order).

Rejected: closing the historical POs without receiving. That leaves the
placeholder rows as the only record, and they carry no price, no supplier and
no order link — the Tapmatic's $2,005.80 would exist nowhere in stock. Scott
chose provenance over leaving the assumed quantities untouched.
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth import get_user_model          # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from stock.models import StockItem, StockLocation       # noqa: E402

TODAY = "2026-08-23"

EB = "SLN/Electronics Bench"
RB12 = "SLN/Electronics Bench/Red Bins/RB-12"
B3R4C8 = "SLN/Bin Wall/B3/B3-R4C8"
RACK = "SLN/Machine Shop/Toolholder Rack"
SHOP = "SLN/Machine Shop"
UNFILED = "SLN/Machine Shop/Unfiled - Machine Shop"

HIST = (f"Received {TODAY} against {{po}} ({{sref}}, ordered {{date}}) to close a "
        "historical order. QUANTITY IS THE PURCHASED QUANTITY FROM THE ORDER, NOT A "
        "PHYSICAL COUNT — no stocktake_date. Settle on the machine-shop walk. "
        "Replaces the [CONFIRMED OWNED — NOT COUNTED] placeholder row of 2026-08-19, "
        "which assumed qty 1.")
DISC = (" DISCREPANCY: the order says {q}, the placeholder assumed 1. Neither was ever "
        "counted.")

# (po_reference, part_pk, qty, location_pathstring, note)
PLAN = [
    # --- Class A: new goods, confirmed in hand -------------------------------
    ("PO-0134", 1057, 1, EB,
     f"Received {TODAY} against PO-0134. In service on the electronics bench — this is "
     "the printer that drives the shop labelling pipeline. Counted 1 because one "
     "printer is present and running."),
    ("PO-0136", 1069, 1, EB,
     f"Received {TODAY} against PO-0136; Amazon shows delivered 2026-08-17, Scott "
     f"confirmed in hand {TODAY}. Counted 1 because one pack is present — the sheet "
     "count inside it was NOT verified. Bench placement is PROVISIONAL: label stock "
     "has no dedicated home yet."),
    ("PO-0030", 1056, 1, EB,
     f"Received {TODAY} against PO-0030, Scott confirmed in hand. Filed at the bench "
     "with the other test gear (UT210E clamp meter). No dedicated instrument drawer "
     "chosen yet."),
    ("PO-0028", 292, 2, RB12,
     f"Received {TODAY} against PO-0028. Two of the four to the RAT GDO Florida pair "
     "(BO-0009), which was confirmed short exactly 2. RB-12 had been sitting empty "
     "waiting for this order."),
    ("PO-0028", 292, 2, B3R4C8,
     f"Received {TODAY} against PO-0028. The two SPARES, to the part's default_location "
     "— a project bin is not where a spare goes home."),

    # --- Class C: historical Tormach / MSC -----------------------------------
    ("PO-0025", 535, 2, RACK, "HIST+DISC"),
    ("PO-0025", 536, 2, RACK, "HIST+DISC"),
    ("PO-0025", 537, 2, RACK, "HIST+DISC"),
    ("PO-0025", 538, 1, RACK, "HIST"),
    ("PO-0025", 539, 8, UNFILED, "HIST-NOPLACEHOLDER"),
    ("PO-0026", 540, 2, SHOP, "HIST+DISC"),
    ("PO-0026", 541, 1, SHOP, "HIST"),
    ("PO-0026", 542, 1, SHOP, "HIST"),
    ("PO-0026", 543, 1, UNFILED, "HIST-NOPLACEHOLDER"),
    ("PO-0026", 544, 1, RACK, "HIST"),
    ("PO-0026", 539, 1, UNFILED, "HIST-NOPLACEHOLDER"),
    ("PO-0027", 927, 1, UNFILED, "HIST-NOPLACEHOLDER"),
]

# Placeholder rows to remove once their part has been received. Matched
# defensively: right part, NO purchase order, and the exact marker text.
PLACEHOLDER_PARTS = [535, 536, 537, 538, 540, 541, 542, 544]
MARKER = "[CONFIRMED OWNED"

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
if not user:
    sys.exit("no superuser to attribute the receive to")


def loc(path):
    l = StockLocation.objects.filter(pathstring=path).first()
    if not l:
        sys.exit(f"MISSING LOCATION: {path}")
    return l


def note_for(tag, po, qty):
    if not tag.startswith("HIST"):
        return tag
    n = HIST.format(po=po.reference, sref=po.supplier_reference, date=po.issue_date)
    if tag == "HIST-NOPLACEHOLDER":
        n = n.replace(" Replaces the [CONFIRMED OWNED — NOT COUNTED] placeholder row of "
                      "2026-08-19, which assumed qty 1.",
                      " There was NO prior stock row for this part at all — it was owned "
                      "and invisible.")
    if tag == "HIST+DISC":
        n += DISC.format(q=qty)
    return n


print("=" * 78)
print("PART 1 — receives")
print("=" * 78)

for po_ref, part_pk, qty, path, tag in PLAN:
    po = PurchaseOrder.objects.filter(reference=po_ref).first()
    if not po:
        print(f"  !! no such PO {po_ref}")
        continue
    line = next((l for l in po.lines.all()
                 if l.part and l.part.part_id == part_pk), None)
    if not line:
        print(f"  !! {po_ref}: no line for part {part_pk}")
        continue
    outstanding = float(line.quantity) - float(line.received or 0)
    dest = loc(path)
    print(f"\n  {po_ref} line {line.pk} part [{part_pk}] {line.part.part.name[:48]}")
    print(f"    receive {qty:g} of {outstanding:g} outstanding -> {path}")
    if outstanding <= 0:
        print("    SKIP — nothing outstanding")
        continue
    if qty > outstanding:
        print(f"    SKIP — plan wants {qty:g} but only {outstanding:g} outstanding")
        continue
    if a.commit:
        po.receive_line_item(line, dest, qty, user,
                             notes=note_for(tag, po, int(line.quantity)))
        print("    RECEIVED")

print("\n" + "=" * 78)
print("PART 2 — PO-0016 bookkeeping (no stock written)")
print("=" * 78)
po16 = PurchaseOrder.objects.get(reference="PO-0016")
l16 = po16.lines.first()
have = StockItem.objects.filter(purchase_order=po16)
tot = sum(float(i.quantity) for i in have)
print(f"  line {l16.pk}: quantity={float(l16.quantity):g} received={float(l16.received or 0):g}")
print(f"  stock already tagged to PO-0016: {tot:g} across {have.count()} rows")
print(f"  -> set received={float(l16.quantity):g}, create NO stock")
if a.commit:
    PurchaseOrderLineItem.objects.filter(pk=l16.pk).update(received=l16.quantity)
    l16.refresh_from_db()
    print(f"  VERIFY received now = {float(l16.received):g}")

print("\n" + "=" * 78)
print("PART 3 — delete superseded placeholder rows")
print("=" * 78)
for pk in PLACEHOLDER_PARTS:
    rows = StockItem.objects.filter(part_id=pk, purchase_order=None,
                                    notes__startswith=MARKER)
    fresh = StockItem.objects.filter(part_id=pk).exclude(purchase_order=None)
    for r in rows:
        print(f"  part [{pk}] placeholder item {r.pk} qty={float(r.quantity):g} @ {r.location}")
        if not fresh.exists():
            print("    KEEP — no PO-backed row exists for this part; refusing to delete")
            continue
        print(f"    replaced by {fresh.count()} PO-backed row(s) -> DELETE")
        if a.commit:
            r.delete()

print("\n" + "=" * 78)
print("VERIFY — final state")
print("=" * 78)
for ref in ("PO-0016", "PO-0025", "PO-0026", "PO-0027", "PO-0028",
            "PO-0030", "PO-0134", "PO-0136"):
    po = PurchaseOrder.objects.filter(reference=ref).first()
    po.refresh_from_db()
    out = sum(1 for l in po.lines.all()
              if float(l.received or 0) < float(l.quantity))
    print(f"  {ref:9s} {po.get_status_display():10s} lines={po.lines.count()} outstanding={out}")

print("\nstock now on the touched parts:")
for pk in sorted({p for _, p, _, _, _ in PLAN} | {12}):
    items = StockItem.objects.filter(part_id=pk)
    tot = sum(float(i.quantity) for i in items)
    name = items.first().part.name[:44] if items else f"part {pk}"
    print(f"  [{pk}] {name:44s} total={tot:g} rows={items.count()}")
    for i in items:
        st = i.stocktake_date or "no stocktake"
        print(f"        {float(i.quantity):g} @ {i.location.name if i.location else '-'}  "
              f"po={i.purchase_order.reference if i.purchase_order else '-'}  {st}")

print("\n" + ("WROTE" if a.commit else "DRY RUN — add --commit"))
