"""athom-tech-new-vendor, part 2: the in-service location and both POs.

RESUME script. athom_chain_0922.py created the company (#36), part (#1257) and
supplier part (#748, pack verified 2 / 2.0) and then died on the location:

    TypeError: StockLocation() got unexpected keyword arguments: 'notes'

StockLocation has NO notes field at all -- unlike Part, Company and
PurchaseOrder, which all do. Long-form context goes in `description`, which is
declared max_length=250 and IS NOT ENFORCED: SLN/Mechanical Room (#620) already
holds 410 characters. That row is also the closest precedent for what this
location is for, so this description is written in the same voice and kept
inside the longest length already in use rather than the declared one.

Idempotent: re-fetches what part 1 made, and refuses if a PO already exists.

    itq run scripts/athom_chain2_0922.py            # dry run
    itq run scripts/athom_chain2_0922.py --commit
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
from stock.models import StockLocation  # noqa: E402

PACK = 2
UNIT = "17.50"
IN_SERVICE = "In Service - HA devices"

LOC_DESC = (
    "IN SERVICE - deployed HA devices, NOT spares. DO NOT PICK FROM THIS "
    "LOCATION. Small network/HA gear in use that moves outlet to outlet "
    "without paperwork, so per-room rows would decay silently. One level "
    "coarser than the room locations. NEVER a default_location - that is "
    "where a spare goes home, and nothing here is spare. Which device runs "
    "what lives in Home Assistant, keyed by ESPHome hostname."
)

ORDERS = [
    ("54653", datetime.date(2026, 8, 17), 3, 52.50, 9.00, True),
    ("56290", datetime.date(2026, 9, 20), 5, 87.50, 12.00, False),
]

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

print("=" * 70)
print("PREFLIGHT -- resume state from part 1")
print("=" * 70)
co = Company.objects.get(name="Athom Tech")
sp = SupplierPart.objects.get(SKU="PG03V2-US16A-ESP-2")
print(f"  company  #{co.pk} {co.name} supplier={co.is_supplier} "
      f"manufacturer={co.is_manufacturer}")
print(f"  part     #{sp.part.pk} IPN={sp.part.IPN}")
print(f"  sp       #{sp.pk} SKU={sp.SKU} pack={sp.pack_quantity} "
      f"native={sp.pack_quantity_native}")
# Re-verify the pack AGAIN here, in the script that leads to the receive.
# This is the field that decides whether 3 units book 3 pieces or 6.
assert float(sp.pack_quantity_native) == float(PACK), \
    f"pack_quantity_native is {sp.pack_quantity_native}, refusing to build POs"
print(f"  pack_quantity_native re-verified = {sp.pack_quantity_native} -- OK")

sln = StockLocation.objects.get(pk=1)
loc = StockLocation.objects.filter(name=IN_SERVICE).first()
print(f"  location: {'EXISTS #%d' % loc.pk if loc else 'not yet created'}")
print(f"  LOC_DESC is {len(LOC_DESC)} chars "
      f"(declared max 250, not enforced; longest in use is 410 on #620)")
assert len(LOC_DESC) <= 410, "description longer than anything already in use"

for order, _, qty, sub, ship, _ in ORDERS:
    dup = PurchaseOrder.objects.filter(Q(supplier_reference=order) | Q(reference=order))
    if dup.exists():
        sys.exit(f"!! PO already exists for {order}: {[p.reference for p in dup]}")
    assert abs(float(UNIT) * qty - sub) < 0.005, f"{order} does not reconcile"
    print(f"  {order}: {qty} x ${UNIT} = ${sub:.2f} = {qty * PACK} pieces "
          f"@ ${sub / (qty * PACK):.2f}  (+${ship:.2f} ship, excluded)")

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --commit")

print()
print("=" * 70)
print("WRITES")
print("=" * 70)

if loc is None:
    loc = StockLocation(name=IN_SERVICE, parent=sln, description=LOC_DESC,
                        structural=False, external=False)
    loc.save()
    loc.refresh_from_db()
    assert loc.parent_id == sln.pk, "parent did not stick"
    assert loc.pathstring == f"SLN/{IN_SERVICE}", f"pathstring wrong: {loc.pathstring}"
    assert not loc.structural, "structural must be False -- it has to hold stock"
    assert loc.description == LOC_DESC, "description did not stick (truncated?)"
    print(f"  CREATED location #{loc.pk} {loc.pathstring}")
    print(f"          description {len(loc.description)} chars, verified intact")
else:
    print(f"  location #{loc.pk} already exists -- left alone")

made = []
for order, issue, qty, sub, ship, receive_later in ORDERS:
    tail = ("RECEIVED by athom_receive_0922.py -- the goods are physically in "
            "the building and have been since August."
            if receive_later else
            "PLACED and IN TRANSIT - shipped 2026-09-21. Do NOT receive until "
            "the goods land and a human checks them in.")
    po = PurchaseOrder(
        supplier=co,
        reference=PurchaseOrder.generate_reference(),
        supplier_reference=order,
        description=f"athom.tech order {order} -- Athom US V2 ESPHome smart plug",
        issue_date=issue,
        status=PurchaseOrderStatus.PLACED.value,
        notes=(f"athom.tech order {order}, placed {issue}. Created 2026-09-22 "
               "from decision item `athom-tech-new-vendor`.\n\n"
               f"PRICE: {qty} units x USD {UNIT} = USD {sub:.2f} item subtotal, "
               f"plus USD {ship:.2f} shipping = USD {sub + ship:.2f} charged. "
               "The line is booked at the ITEM price only. Shipping is "
               "deliberately excluded -- folding it in would inflate the piece "
               "cost permanently, the same trap already written down for eBay "
               "and AliExpress.\n\n"
               f"PACK: one unit is a TWO-PACK, so {qty} units = {qty * PACK} "
               f"plugs at USD {sub / (qty * PACK):.2f} each. The supplier part "
               f"carries pack_quantity=2; receiving at pack 1 would book {qty} "
               f"plugs instead of {qty * PACK}.\n\n"
               "PAID VIA PAYPAL, which is why this order surfaced to the sweep "
               "as a paypal.com sender and not as athom.tech, and why it sat "
               "unimported behind an unknown-vendor decision.\n\n"
               "The vendor order number is in supplier_reference, NOT in "
               "reference -- a raw vendor number in reference clamps "
               "reference_int to int32 max and permanently breaks "
               "generate_reference() for the whole instance.\n\n"
               f"{tail}"),
    )
    po.save()
    po.refresh_from_db()
    assert po.supplier_reference == order, "supplier_reference did not stick"
    assert po.reference != order, "vendor number leaked into reference"
    assert po.reference_int < 2 ** 31 - 1, "reference_int clamped"
    assert po.status == PurchaseOrderStatus.PLACED.value, "status did not stick"

    li = PurchaseOrderLineItem(
        order=po, part=sp, quantity=qty,
        purchase_price=UNIT, purchase_price_currency="USD",
        notes=(f"{qty} x 2-pack at USD {UNIT} per pack = {qty * PACK} plugs. "
               f"Shipping USD {ship:.2f} excluded."))
    li.save()
    li.refresh_from_db()
    assert float(li.purchase_price.amount) == float(UNIT), "price did not stick"

    booked = sum(float(l.purchase_price.amount) * float(l.quantity)
                 for l in po.lines.all())
    assert abs(booked - sub) < 0.005, f"{po.reference} booked total drifted"
    print(f"  CREATED {po.reference} supplier_ref={po.supplier_reference} "
          f"ref_int={po.reference_int} PLACED")
    print(f"          qty={li.quantity} @ {li.purchase_price} booked=${booked:.2f}")
    made.append((po, qty))

print()
print("=" * 70)
print("STATE")
print("=" * 70)
print(f"  company  #{co.pk}  {co.name}")
print(f"  part     #{sp.part.pk}  {sp.part.name}")
print(f"  sp       #{sp.pk}  pack={sp.pack_quantity} native={sp.pack_quantity_native}")
print(f"  location #{loc.pk}  {loc.pathstring}")
for po, qty in made:
    print(f"  {po.reference}  vendor {po.supplier_reference}  {qty} units = "
          f"{qty * PACK} pieces  {po.get_status_display()}")
print()
print("  STILL OPEN -- needs a fact only Scott has:")
print("    - receive PO for 54653 (6 pieces), split 4 in-service / 2 spare")
print("    - part.default_location = the spares location")
