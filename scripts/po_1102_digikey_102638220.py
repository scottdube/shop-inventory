"""Queue C: DigiKey sales order 102638220 (2026-11-02 ~11:45 EST) -> PO, 1 new part.

PRICE SOURCE -- the DigiKey "Thank you for your DigiKey order!" email, itemised
with separate UNIT and EXTENDED columns:

    732-9170-1-ND                    860040473003             qty 50  unit 0.15100 ext $7.55
    CF14JT10K0CT-ND                  CF14JT10K0               qty 100 unit 0.01740 ext $1.74
    2223-TS11-674-80-BK-160-RA-D-ND  TS11-674-80-BK-160-RA-D  qty 150 unit 0.12150 ext $18.23
    Subtotal $27.52  Shipping $8.49  Sales tax $2.53  Tariff $8.68  Total $47.22

Booked at UNIT price; shipping, tax and tariff are order-level and not spread
(same rule as po_1004_digikey_relay_47k.py). Ship-to LRD.

REUSE vs CREATE, from probe_1102_digikey_dupes.py the same run:
- 100uF 25V -> REUSE #1463 "Capacitor Electrolytic 100uF 25V". Its name carries
  no can size, unlike #686/#695/#1423, so it is the size-agnostic row; the
  order mail gives no can size either. A new part would split one value into
  two shelves for no stated reason (one stock row per interchangeable part).
- 10k -> REUSE #1462 "Resistor 10k 5% 1/4W carbon film": same identity exactly
  (CF14JT10K0 is a 5% 1/4W carbon film axial). NOT #634, which is 1% metal film.
- TS11 right-angle tactile -> NEW part. #1461 is a 6x6x9mm right-angle switch;
  the mail states neither body size nor height, and the cancelled Amazon order
  113-9633331-6297034 the same weekend was for 6x6x8mm, so height evidently
  matters to whoever is buying. Merging on a guess is the error that cannot be
  seen later; a separate part can be merged once the switch is in hand.
  Name carries only what the mail states; manufacturer NOT asserted (mail gives
  the MPN only), matching the 2026-10-04 DigiKey import.

PACK 1 on all three new DigiKey supplier parts (cut tape, priced per piece).
TARGET DATE NULL (no ETA in the confirmation). PLACED, never received.
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
from part.models import Part  # noqa: E402
from plugins.notes_compat import note_set, note_text  # noqa: E402

# InvenTree 1.6 moved notes to common.Note rows: `notes=` on PurchaseOrder and
# Part is a read-only property, so the first --commit died in the constructor
# (nothing written). PO and part notes go through notes_compat; line-item
# notes are still a plain field.

ORDER = "102638220"
ISSUE = datetime.date(2026, 11, 2)
SUBTOTAL = 27.52
SHIPPING, TAX, TARIFF, TOTAL = 8.49, 2.53, 8.68, 47.22

LINES = [
    dict(sku="732-9170-1-ND", mpn="860040473003", unit="0.151", qty=50,
         reuse=1463, reuse_name="Capacitor Electrolytic 100uF 25V"),
    dict(sku="CF14JT10K0CT-ND", mpn="CF14JT10K0", unit="0.0174", qty=100,
         reuse=1462, reuse_name="Resistor 10k 5% 1/4W carbon film"),
    dict(sku="2223-TS11-674-80-BK-160-RA-D-ND", mpn="TS11-674-80-BK-160-RA-D",
         unit="0.1215", qty=150, reuse=None,
         cat_from=1461, cat_path="Switches",
         name="Tactile Switch right angle, SPST-NO 0.05A 12V (TS11-674-80-BK-160-RA-D)",
         desc=("orig: SWITCH TACTILE SPST-NO 0.05A 12V (DigiKey "
               "2223-TS11-674-80-BK-160-RA-D-ND, MPN TS11-674-80-BK-160-RA-D)"),
         ipn="TS11-674-80-BK-160-RA-D",
         kw=("tactile switch, tact switch, pushbutton, momentary, right angle, "
             "right-angle, RA, SPST-NO, PCB, through-hole, TS11, "
             "TS11-674-80-BK-160-RA-D, 2223-TS11-674-80-BK-160-RA-D-ND, black"),
         dupe_terms=["TS11-674", "TS11674", "2223-TS11"],
         notes=("Right-angle PCB tactile switch, SPST-NO, rated 0.05 A 12 V, MPN "
                "TS11-674-80-BK-160-RA-D. Body size, height and actuation force "
                "are NOT recorded: the order mail states none of them. "
                "Not merged with #1461 (6x6x9 mm right angle) for that reason; "
                "merge once one is in hand and measured.\n\n"
                "Created by the queue C daytime sweep, 12:40 run 2026-11-02, "
                f"from DigiKey sales order {ORDER}.")),
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
    if SupplierPart.objects.filter(supplier=dk, SKU=ln["sku"]).exists():
        sys.exit(f"!! supplier part {ln['sku']} already exists — resolve by hand")
    if ln["reuse"]:
        p = Part.objects.get(pk=ln["reuse"])
        assert p.name == ln["reuse_name"], f"#{p.pk} renamed: {p.name!r}"
        assert p.active, f"#{p.pk} inactive"
        print(f"  {ln['sku']}: REUSE #{p.pk} {p.name}  qty {ln['qty']} @ {ln['unit']}")
    else:
        q = Q(IPN=ln["ipn"])
        for t in ln["dupe_terms"]:
            q |= (Q(name__icontains=t) | Q(description__icontains=t)
                  | Q(IPN__icontains=t) | Q(keywords__icontains=t))
        dupes = Part.objects.filter(q).distinct()
        for d in dupes:
            print(f"  possible dupe: #{d.pk} active={d.active} {d.name}")
        if dupes.exists():
            sys.exit(f"!! a part for {ln['mpn']} already exists — resolve by hand")
        assert len(ln["kw"]) <= 250, f"keywords too long: {len(ln['kw'])}"
        assert len(ln["name"]) <= 100, f"name too long: {len(ln['name'])}"
        cat = Part.objects.get(pk=ln["cat_from"]).category
        assert cat.pathstring == ln["cat_path"], f"category moved: {cat.pathstring}"
        print(f"  {ln['sku']}: NEW in {cat.pathstring}  qty {ln['qty']} @ {ln['unit']}"
              f"  kw {len(ln['kw'])} chars")

total = sum(float(l["unit"]) * l["qty"] for l in LINES)
print(f"reconcile: lines sum {total:.3f} vs email SUBTOTAL {SUBTOTAL:.2f} "
      f"(total {TOTAL:.2f} incl shipping {SHIPPING:.2f}, tax {TAX:.2f}, tariff {TARIFF:.2f})")
assert abs(total - SUBTOTAL) < 0.01, "line prices do not reconcile — refusing"

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ---------------------------------------------------------------- PO
po = PurchaseOrder(
    supplier=dk,
    reference=PurchaseOrder.generate_reference(),
    supplier_reference=ORDER,
    description=(f"DigiKey sales order {ORDER} — 100uF 25V x50, 10k 5% x100, "
                 "TS11 right-angle tactile x150"),
    issue_date=ISSUE,
    status=PurchaseOrderStatus.PLACED.value,
)
po.save()
note_set(po, ("Auto-created by the queue C daytime sweep, 12:40 run 2026-11-02.\n\n"
           "PRICE SOURCE: the DigiKey order-placed email (separate unit and "
           "extended columns). 732-9170-1-ND 50 x $0.151 = $7.55; "
           "CF14JT10K0CT-ND 100 x $0.0174 = $1.74; "
           "2223-TS11-674-80-BK-160-RA-D-ND 150 x $0.1215 = $18.23; subtotal "
           "$27.52. Shipping $8.49, tax $2.53, tariff $8.68 (total $47.22) are "
           "order-level and deliberately not spread over the lines.\n\n"
           "Ships to LRD. TARGET DATE empty: the confirmation carries no ETA.\n\n"
           "PLACED, not received. Receive with receive_po.py when checked in."))
po.refresh_from_db()
assert note_text(po).startswith("Auto-created"), "PO note did not stick"
assert po.status == PurchaseOrderStatus.PLACED.value, "PO status did not stick"
assert po.supplier_reference == ORDER, "supplier_reference did not stick"
assert po.reference != ORDER, "vendor number leaked into reference"
print(f"\nCREATED {po.reference} supplier_ref={po.supplier_reference}")

for ln in LINES:
    if ln["reuse"]:
        part = Part.objects.get(pk=ln["reuse"])
    else:
        cat = Part.objects.get(pk=ln["cat_from"]).category
        part = Part(name=ln["name"], description=ln["desc"], category=cat,
                    IPN=ln["ipn"], keywords=ln["kw"], component=True,
                    purchaseable=True, assembly=False)
        part.save()
        note_set(part, ln["notes"])
        part.refresh_from_db()
        assert note_text(part).startswith("Right-angle"), "part note did not stick"
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
    print(f"    sp #{sp.pk} part #{part.pk} SKU={sp.SKU} pack={sp.pack_quantity} "
          f"native={sp.pack_quantity_native}")

    li = PurchaseOrderLineItem(
        order=po, part=sp, quantity=ln["qty"],
        purchase_price=ln["unit"], purchase_price_currency="USD",
        notes=(f"Unit price from the DigiKey order email: {ln['qty']} x "
               f"${ln['unit']}. Shipping, tax and tariff excluded."))
    li.save()
    li.refresh_from_db()
    assert float(li.purchase_price.amount) == float(ln["unit"]), \
        f"price did not stick: {li.purchase_price}"
    print(f"    line: qty {li.quantity} @ {li.purchase_price}")

po.refresh_from_db()
booked = sum(float(l.purchase_price.amount) * float(l.quantity)
             for l in po.lines.all())
print(f"\nDONE  {po.reference}  lines={po.lines.count()}  booked=${booked:.3f}"
      f"  (email subtotal ${SUBTOTAL:.2f})")
assert abs(booked - SUBTOTAL) < 0.01, "booked total drifted from the email"
