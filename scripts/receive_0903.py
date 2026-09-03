"""Receive the 2026-09-03 arrivals: seven POs, one deliberately left open.

Scott has all of these in hand and told me where each goes, so every row here
carries a stocktake stamp — a put-away performed by a person IS a count, unlike
a PO receipt on its own.

    PO-0150  LA38 push buttons x3   -> Assembly & Test   (pack of 3)
    PO-0151  YF-S401 flow sensors   -> B3-R7C2 x1, Assembly & Test x1 (pack of 2)
    PO-0152  INA228 module          -> Assembly & Test
    PO-0153  MC-9b contactor        -> Assembly & Test
    PO-0154  battery lug crimper    -> Receiving
    PO-0156  terminal brush         -> Receiving
    PO-0157  brake line flaring kit -> Receiving
    PO-0155  6 AWG cable kit        -> NOT RECEIVED. Arrived, being returned.

NO LINE REPAIR IS NEEDED AND THAT IS A CHANGE. The PO-0139 precedent rewrote a
line from packs into pieces because receive_line_item was believed to drop
pack_quantity. Read on the Mini 2026-09-03, this version does not drop it:

    stock_quantity = supplier_part.base_quantity(quantity)     # x pack_quantity
    purchase_price = line.purchase_price / supplier_part.base_quantity(1)
    line.received  += quantity                                 # in LINE units

So the receive quantity is PACKS, the stock row lands in PIECES, and the price
is divided per piece by the same factor. All four supplier parts already carry
the right pack_quantity (3, 2, 1, 1), so the honest move is to leave the lines
alone and let the code do it. The qty x price == line total assertion below is
what proves it rather than trusting the read.

DEFAULT_LOCATION IS SET ONLY FOR THE FLOW SENSOR. The assembly table is where
the shrink-fit rig is being worked and Receiving is a staging dock; neither is
where a spare goes home, and pointing a default at one blesses the backlog.
B3-R7C2 genuinely is the flow sensor's home, so it gets one.

    itq run scripts/receive_0903.py             # dry run
    itq run scripts/receive_0903.py --commit
"""
import argparse
import datetime
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth import get_user_model            # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from part.models import Part                              # noqa: E402
from stock.models import StockItem, StockLocation         # noqa: E402

TODAY = datetime.date.today()
AT, B3R7C2, RECV = 459, 335, 472        # pks, because "Receiving" is not a unique name

AT_NOTE = (
    "ON THE ASSEMBLY TABLE — in work, not filed. Received {po} on %s, Scott "
    "confirmed it in hand and put it on the assembly table with the rest of the "
    "shrink-fit rig (BO-0002). This is a whereabouts, not a home: the part has "
    "no default_location on purpose, because a staging area must not be blessed "
    "as one." % TODAY
)

RECV_NOTE = (
    "Received {po} on %s and left in Receiving — Scott confirmed it arrived, no "
    "home chosen yet. RECEIVING IS THE BLIND SPOT: a row here that gets used on "
    "the way past is never looked at again, so this needs a drawer or a "
    "belongs_to before it goes quiet." % TODAY
)

PLAN = [
    # (po ref, line pk, destination pk, pieces expected, note)
    ("PO-0150", 173, AT, 3, AT_NOTE.format(po="PO-0150") + (
        "\n\nTHREE buttons, one each red / yellow / green, 22 mm, 1NO+1NC. "
        "Scott: \"the push button switches (3) are here and at the assy table\" "
        "— his count, not the order line's. Verify the 22 mm cutout against the "
        "LA39 E-stop before any panel is cut.")),
    ("PO-0151", 174, B3R7C2, 2, (
        "Received PO-0151 on %s, one pack of TWO counted in hand by Scott. Both "
        "land here first because B3-R7C2 is this part's HOME; one is then split "
        "out to the assembly table for the shrink-fit coolant loop.\n\n"
        "Set CR-06's low-flow trip ABOVE the sensor's 0.3 L/min floor, not at "
        "it, or a slowing turbine nuisance-trips mid-cycle." % TODAY)),
    ("PO-0152", 175, AT, 1, AT_NOTE.format(po="PO-0152") + (
        "\n\nTHE ONBOARD R002 SHUNT HAS BEEN REMOVED — this module is set up for "
        "an EXTERNAL shunt and cannot measure current on its own any more. "
        "VIN+ to VIN- read 35 MOhm after the rework, which is open for this "
        "purpose. Bring-up passed on a NodeMCU-32S: MFG_ID 0x5449, DEVICE_ID "
        "0x2281, OTA as shrinkfit-ina228.local. The removed resistor is stocked "
        "separately — see the current-sense resistor part in B3-R3C2.")),
    ("PO-0153", 176, AT, 1, AT_NOTE.format(po="PO-0153") + (
        "\n\nBefore it is wired: confirm the COIL is 24 V DC and that the "
        "contacts carry the AC rating rather than the 24 V the Amazon listing "
        "pasted onto them. The third main pole stays UNUSED — the 12 V rail "
        "must not be on it (requirements 6.9).")),
    ("PO-0154", 177, RECV, 1, RECV_NOTE.format(po="PO-0154")),
    ("PO-0156", 179, RECV, 1, RECV_NOTE.format(po="PO-0156")),
    ("PO-0157", 180, RECV, 1, RECV_NOTE.format(po="PO-0157")),
]

# The flow sensor split: one piece leaves B3-R7C2 for the assembly table.
SPLIT_LINE = 174
SPLIT_NOTE = (
    "ON THE ASSEMBLY TABLE — in work, not filed. Split off the B3-R7C2 pair on "
    "%s for the shrink-fit coolant loop (BO-0002). Scott: \"need to put one "
    "away and one at the assy table\". Its twin is the spare at home in "
    "B3-R7C2." % TODAY
)

RETURN_REF, RETURN_LINE = "PO-0155", 178
RETURN_NOTE = (
    "ARRIVED %s AND IS BEING RETURNED — deliberately NOT received. Scott, "
    "2026-09-03: the wire is going back. No stock row exists for it and none "
    "should be created; the order is left PLACED rather than marked Returned "
    "because the return has not completed yet, and an open PO is the only thing "
    "that will keep asking about the refund. Close it when the credit lands." % TODAY
)

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
locs = {pk: StockLocation.objects.get(pk=pk) for pk in (AT, B3R7C2, RECV)}
for pk, loc in locs.items():
    print(f"dest [{pk}] {loc.pathstring}")
print()

# ---- pre-flight: every line must be unreceived, PLACED, and price-consistent
ok = True
for ref, line_pk, dest, pieces, _note in PLAN:
    po = PurchaseOrder.objects.get(reference=ref)
    line = PurchaseOrderLineItem.objects.get(pk=line_pk)
    sp = line.part
    packs = float(line.quantity) - float(line.received)
    computed = float(sp.base_quantity(packs))
    unit = (float(line.purchase_price.amount) / float(sp.base_quantity(1))
            if line.purchase_price else 0.0)
    ext_line = float(line.purchase_price.amount) * float(line.quantity) if line.purchase_price else 0.0
    ext_stock = unit * computed
    flag = ""
    if po.status != 20:
        flag += "  !! not PLACED"
        ok = False
    if float(line.received) != 0:
        flag += "  !! already partly received"
        ok = False
    if abs(computed - pieces) > 1e-9:
        flag += f"  !! expected {pieces} pieces, code gives {computed:g}"
        ok = False
    if abs(ext_line - ext_stock) > 0.005:
        flag += f"  !! price {ext_line} vs {ext_stock}"
        ok = False
    print(f"{ref} line {line_pk}: {packs:g} pack(s) x pack_quantity "
          f"{sp.pack_quantity_native.normalize():g} = {computed:g} pieces "
          f"@ ${unit:.6f}  (line total ${ext_line:.2f})  -> {locs[dest].name}{flag}")
    print(f"    {sp.part.name[:88]}")

rpo = PurchaseOrder.objects.get(reference=RETURN_REF)
rline = PurchaseOrderLineItem.objects.get(pk=RETURN_LINE)
print(f"\n{RETURN_REF} line {RETURN_LINE}: NOT RECEIVED (being returned) — "
      f"{rline.part.part.name[:60]}, ${rline.purchase_price}")

if not ok:
    sys.exit("\npre-flight FAILED — nothing written")
if not a.commit:
    sys.exit("\nDRY RUN — add --commit")

# ---- receive -------------------------------------------------------------
print()
created = {}
for ref, line_pk, dest, pieces, note in PLAN:
    po = PurchaseOrder.objects.get(reference=ref)
    line = PurchaseOrderLineItem.objects.get(pk=line_pk)
    packs = line.quantity - line.received
    before = set(StockItem.objects.filter(purchase_order=po).values_list("pk", flat=True))
    po.receive_line_item(line, locs[dest], packs, user)
    after = set(StockItem.objects.filter(purchase_order=po).values_list("pk", flat=True))
    new = list(after - before)
    if len(new) != 1:
        sys.exit(f"{ref}: expected 1 new stock row, got {len(new)} — STOPPING")
    si = StockItem.objects.get(pk=new[0])
    StockItem.objects.filter(pk=si.pk).update(
        notes=note, stocktake_date=TODAY, stocktake_user=user)
    created[line_pk] = si.pk
    si.refresh_from_db()
    print(f"{ref}: stock #{si.pk}  {float(si.quantity):g} x "
          f"{si.part.name[:44]}  @ {si.location.name}  ${si.purchase_price}")

# ---- split one flow sensor out to the assembly table ---------------------
src = StockItem.objects.get(pk=created[SPLIT_LINE])
new_si = src.splitStock(1, locs[AT], user,
                        notes="One of the pair to the assembly table, shrink-fit coolant loop.")
if new_si is None:
    sys.exit("flow sensor split returned None — STOPPING")
StockItem.objects.filter(pk=new_si.pk).update(
    notes=SPLIT_NOTE, stocktake_date=TODAY, stocktake_user=user)
src.refresh_from_db()
new_si.refresh_from_db()
print(f"split: #{src.pk} {float(src.quantity):g} @ {src.location.name}  ->  "
      f"#{new_si.pk} {float(new_si.quantity):g} @ {new_si.location.name}")

# ---- the flow sensor gets a real home; nothing else does -----------------
Part.objects.filter(pk=src.part_id).update(default_location=locs[B3R7C2])

# ---- the returned order ---------------------------------------------------
PurchaseOrderLineItem.objects.filter(pk=RETURN_LINE).update(
    notes=((rline.notes or "").strip() + "\n\n" + RETURN_NOTE).strip())
PurchaseOrder.objects.filter(pk=rpo.pk).update(
    notes=((rpo.notes or "").strip() + "\n\n" + RETURN_NOTE).strip())

# ---- verify ---------------------------------------------------------------
print("\n--- verify ---")
fail = 0
for ref, line_pk, dest, pieces, _n in PLAN:
    po = PurchaseOrder.objects.get(reference=ref)
    line = PurchaseOrderLineItem.objects.get(pk=line_pk)
    rows = list(StockItem.objects.filter(purchase_order=po))
    total = sum(float(r.quantity) for r in rows)
    booked = sum(float(r.quantity) * float(r.purchase_price.amount)
                 for r in rows if r.purchase_price)
    ext = float(line.purchase_price.amount) * float(line.quantity)
    stamped = all(r.stocktake_date == TODAY for r in rows)
    bad = []
    if abs(total - pieces) > 1e-9:
        bad.append(f"pieces {total:g} != {pieces}")
    if abs(booked - ext) > 0.005:
        bad.append(f"booked ${booked:.2f} != line ${ext:.2f}")
    if float(line.received) < float(line.quantity):
        bad.append(f"received {line.received:g}/{line.quantity:g}")
    if not stamped:
        bad.append("stocktake_date missing")
    if po.status != 30:
        bad.append(f"PO status {po.get_status_display()}")
    fail += len(bad)
    print(f"{ref} {po.get_status_display():9s} pieces={total:g} booked=${booked:.2f} "
          f"line=${ext:.2f} {'OK' if not bad else 'FAIL: ' + '; '.join(bad)}")

rpo.refresh_from_db()
rrows = StockItem.objects.filter(purchase_order=rpo).count()
print(f"{RETURN_REF} {rpo.get_status_display():9s} stock rows={rrows} "
      f"{'OK (none, as intended)' if rrows == 0 else 'FAIL — stock was created'}")
if rrows:
    fail += 1
if "BEING RETURNED" not in (rpo.notes or ""):
    print("FAIL: return note did not stick")
    fail += 1

print(f"\n{'SUCCESS' if fail == 0 else 'FAILED'} — {fail} problem(s)")
sys.exit(1 if fail else 0)
