"""Queue C: DigiKey sales order 102025753 (2026-10-04 ~20:50 EDT) -> 2 new parts + PO.

PRICE SOURCE -- the DigiKey "Thank you for your DigiKey order!" email, which is
itemised with separate UNIT and EXTENDED columns:

    PB2031-ND               ORWH-SH-124D1F,000  qty 4   unit 2.39000  ext $9.56
    13-MFP-25BRD52-47KCT-ND MFP-25BRD52-47K     qty 10  unit 0.41000  ext $4.10
    Subtotal $13.66   Shipping $8.49   Sales tax $0.00   Tariff $3.23   Total $25.38

Lines booked at the UNIT price. Shipping and the tariff are order-level charges
and are not spread over the pieces (same rule as eBay/AliExpress). The assert
reconciles against the SUBTOTAL.

RELAY: the coolant relay on the 1100MX ECM1 V1.5 board (both K-relays there are
this part, photographed 2026-10-04; see tormach-1100mx/docs/coolant-outlet-fault.md).
That doc had 3 in the cart as SPARES, "not a repair"; the order placed was 4.
Category Relays (#15), where the other 11 relays live.

RESISTOR: 47k 0.1% 1/4W axial metal film. #622 "Resistor 47k 1% 1/4W" exists
and was deliberately NOT reused -- 1% and 0.1% are not interchangeable, which is
exactly why somebody bought 0.1% (res_47k_lookup_1004.py searched for a 0.1%
part earlier the same day and the order followed). Category
Electronics/Passives/Resistors (#69), beside #622. Manufacturer NOT asserted in
the name: the order mail gives only the MPN.

NO ManufacturerPart rows: neither TE nor the resistor maker exists as a Company
and creating companies is not a sweep decision. MPN goes in IPN and the name,
matching part #820 (A1324LUA-T). SupplierPart SKU = DigiKey PN, link = keyword
search URL, the convention of sp #554/#555.

PACK 1 for both (DigiKey sells singles / cut tape by the piece; unit price is
per piece). TARGET DATE left NULL: the confirmation gives no ETA and inventing
one is worse than an empty field. NO IMAGE. PLACED, never received.
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

ORDER = "102025753"
ISSUE = datetime.date(2026, 10, 4)
SUBTOTAL = 13.66
SHIPPING, TARIFF, TOTAL = 8.49, 3.23, 25.38

LINES = [
    dict(
        sku="PB2031-ND", mpn="ORWH-SH-124D1F,000", ipn="ORWH-SH-124D1F",
        unit="2.39", qty=4, cat=15, cat_path="Relays",
        name="Relay, SPDT 24 VDC coil, 10 A, PCB through-hole, TE/OEG ORWH-SH-124D1F",
        desc="orig: RELAY GEN PURPOSE SPDT 10A 24V (DigiKey PB2031-ND, MPN ORWH-SH-124D1F,000)",
        kw=("relay, SPDT, 24V, 24VDC, coil, PCB relay, through-hole, power relay, "
            "TE, OEG, Tyco, ORWH, ORWH-SH-124D1F, PB2031-ND, Tormach, 1100MX, ECM1, "
            "coolant relay, mist, flood, K3, spare"),
        dupe_terms=["ORWH", "124D1F", "PB2031"],
        notes=("TE / OEG ORWH-SH-124D1F, 24 VDC coil, SPDT, through-hole, 5 pins. "
               "Body marking on the installed ones reads 15 A 125 VAC / 10 A 277 VAC.\n\n"
               "This is the coolant relay on the Tormach 1100MX ECM1 V1.5 control "
               "board (both coolant relays there are this part, soldered, not "
               "socketed). Bought as SPARES during the 2026-10-04 flood-outlet fault "
               "work; see ~/code/tormach-1100mx/docs/coolant-outlet-fault.md. "
               "Swapping one means pulling the board and desoldering 5 pins.\n\n"
               "Created by the queue C daytime sweep, 22:40 run 2026-10-04, from "
               f"DigiKey sales order {ORDER}."),
    ),
    dict(
        sku="13-MFP-25BRD52-47KCT-ND", mpn="MFP-25BRD52-47K", ipn="MFP-25BRD52-47K",
        unit="0.41", qty=10, cat=69, cat_path="Electronics/Passives/Resistors",
        name="Resistor 47k 0.1% 1/4W metal film, axial (MFP-25BRD52-47K)",
        desc="orig: RES 47K OHM 0.1% 1/4W AXIAL (DigiKey 13-MFP-25BRD52-47KCT-ND)",
        kw=("resistor, 47k, 47K, 47kohm, 47000, 473, 0.1%, precision, tolerance B, "
            "1/4W, 0.25W, metal film, axial, through-hole, MFP-25BRD52-47K, "
            "MFP-25, 13-MFP-25BRD52-47KCT-ND"),
        dupe_terms=["MFP-25", "MFP25", "BRD52", "13-MFP"],
        notes=("47 kOhm, 0.1% tolerance, 1/4 W, axial metal film, MPN "
               "MFP-25BRD52-47K.\n\n"
               "NOT interchangeable with #622 (47k 1%, the EAONE kit value). "
               "Keep these apart; 0.1% parts are bought for a reason. What they "
               "are for was not in the order.\n\n"
               "Created by the queue C daytime sweep, 22:40 run 2026-10-04, from "
               f"DigiKey sales order {ORDER}."),
    ),
]

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

dk = Company.objects.get(pk=15)
assert dk.name == "DigiKey", f"company #15 is {dk.name!r}"

# ---------------------------------------------------------------- idempotency
dup_po = PurchaseOrder.objects.filter(
    Q(supplier_reference=ORDER) | Q(reference=ORDER))
if dup_po.exists():
    sys.exit(f"!! PO already exists for {ORDER}: "
             f"{[p.reference for p in dup_po]} — nothing to do")

for ln in LINES:
    q = Q(IPN=ln["ipn"])
    for t in ln["dupe_terms"]:
        q |= (Q(name__icontains=t) | Q(description__icontains=t)
              | Q(IPN__icontains=t) | Q(keywords__icontains=t))
    dupes = Part.objects.filter(q).distinct()
    for d in dupes:
        print(f"  possible dupe: #{d.pk} active={d.active} {d.name}")
    if dupes.exists():
        sys.exit(f"!! a part for {ln['mpn']} already exists — resolve by hand")
    if SupplierPart.objects.filter(supplier=dk, SKU=ln["sku"]).exists():
        sys.exit(f"!! supplier part {ln['sku']} already exists — resolve by hand")
    assert len(ln["kw"]) <= 250, f"keywords too long: {len(ln['kw'])}"
    assert len(ln["name"]) <= 100, f"name too long: {len(ln['name'])}"
    cat = PartCategory.objects.get(pk=ln["cat"])
    assert cat.pathstring == ln["cat_path"], f"category moved: {cat.pathstring}"
    print(f"  {ln['sku']}: qty {ln['qty']} @ {ln['unit']}  cat {cat.pathstring}  "
          f"kw {len(ln['kw'])} chars")

total = sum(float(l["unit"]) * l["qty"] for l in LINES)
print(f"reconcile: lines sum {total:.2f} vs email SUBTOTAL {SUBTOTAL:.2f} "
      f"(order total {TOTAL:.2f} incl ${SHIPPING:.2f} shipping + ${TARIFF:.2f} tariff)")
assert abs(total - SUBTOTAL) < 0.005, "line prices do not reconcile — refusing"

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ---------------------------------------------------------------- PO
po = PurchaseOrder(
    supplier=dk,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=f"DigiKey sales order {ORDER} — ORWH-SH-124D1F relays x4, 47k 0.1% resistors x10",
    issue_date=ISSUE,
    status=PurchaseOrderStatus.PLACED.value,
    notes=("Auto-created by the queue C daytime sweep, 22:40 run 2026-10-04.\n\n"
           "PRICE SOURCE: the DigiKey order-placed email, which has separate unit "
           "and extended columns. PB2031-ND 4 x $2.39 = $9.56; "
           "13-MFP-25BRD52-47KCT-ND 10 x $0.41 = $4.10; subtotal $13.66. "
           "Shipping $8.49 and tariff $3.23 (total $25.38) are order-level and "
           "were deliberately not spread over the lines.\n\n"
           "The relays are spares for the 1100MX ECM1 coolant relays "
           "(tormach-1100mx/docs/coolant-outlet-fault.md).\n\n"
           "TARGET DATE left empty: the confirmation carries no ETA; the ship "
           "notice will.\n\n"
           "PLACED, not received. Receive with receive_po.py when checked in."),
)
po.save()
po.refresh_from_db()
assert po.status == PurchaseOrderStatus.PLACED.value, "PO status did not stick"
assert po.supplier_reference == ORDER, "supplier_reference did not stick"
assert po.reference != ORDER, "vendor number leaked into reference"
print(f"\nCREATED {po.reference} supplier_ref={po.supplier_reference}")

for ln in LINES:
    cat = PartCategory.objects.get(pk=ln["cat"])
    part = Part(name=ln["name"], description=ln["desc"], category=cat,
                IPN=ln["ipn"], keywords=ln["kw"], component=True,
                purchaseable=True, assembly=False, notes=ln["notes"])
    part.save()
    part.refresh_from_db()
    assert part.name == ln["name"], "part name did not stick"
    assert part.category_id == cat.pk, "category did not stick"
    assert part.keywords == ln["kw"], "keywords did not stick"
    assert part.IPN == ln["ipn"], "IPN did not stick"
    print(f"  CREATED part #{part.pk} {part.name}  cat={part.category.pathstring}")

    sp = SupplierPart(
        supplier=dk, part=part, SKU=ln["sku"],
        link=f"https://www.digikey.com/en/products/result?keywords={ln['sku']}",
        note=f"MPN {ln['mpn']}")
    sp.pack_quantity = "1"           # .save() -> clean() -> pack_quantity_native
    sp.save()
    sp.refresh_from_db()
    assert str(sp.pack_quantity) == "1", f"pack text did not stick: {sp.pack_quantity}"
    assert float(sp.pack_quantity_native) == 1.0, \
        f"pack_quantity_native did not stick: {sp.pack_quantity_native}"
    print(f"    sp #{sp.pk} SKU={sp.SKU} pack={sp.pack_quantity} native={sp.pack_quantity_native}")

    li = PurchaseOrderLineItem(
        order=po, part=sp, quantity=ln["qty"],
        purchase_price=ln["unit"], purchase_price_currency="USD",
        notes=(f"Unit price from the DigiKey order email: {ln['qty']} x "
               f"${ln['unit']}. Shipping and tariff excluded."))
    li.save()
    li.refresh_from_db()
    assert float(li.purchase_price.amount) == float(ln["unit"]), \
        f"price did not stick: {li.purchase_price}"
    print(f"    line: qty {li.quantity} @ {li.purchase_price}")

po.refresh_from_db()
booked = sum(float(l.purchase_price.amount) * float(l.quantity)
             for l in po.lines.all())
print(f"\nDONE  {po.reference}  lines={po.lines.count()}  booked=${booked:.2f}"
      f"  (email subtotal ${SUBTOTAL:.2f})")
assert abs(booked - SUBTOTAL) < 0.005, "booked total drifted from the email"
