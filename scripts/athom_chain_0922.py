"""athom-tech-new-vendor: Company + part + supplier part + both POs + location.

Approved by Scott 2026-09-22, together with in-service-bucket-for-portable-devices.
Source of truth: /Volumes/4TB_Removable/inventree/pending_decisions.md (both items).

    itq run scripts/athom_chain_0922.py            # dry run
    itq run scripts/athom_chain_0922.py --commit

WHAT THIS DOES NOT DO: it does not receive PO-0180 and does not set
default_location. Both need facts only Scott has -- which bin the 2 spares
live in, and the date the 4 deployed plugs went in. Those land in a second
script so that everything derivable from the decision item can be written now.

THE PACK TRAP, which is the whole reason this script is careful:
the vendor order line reads `pcs 2PACKS`. The USD 17.50 unit IS A TWO-PACK.
So 3 units = 6 plugs and 5 units = 10 plugs, 16 plugs total at USD 8.75 each.
`pack_quantity` MUST be 2 on the supplier part before receive_po.py runs, or 3
units book 3 pieces at 17.50 instead of 6 at 8.75.

The pack is stored TWICE and only `pack_quantity_native` is read at receive
time: `clean()` derives it from the text field and `save()` calls `clean()`, so
a queryset `.update(pack_quantity='2')` changes every screen and nothing that
counts. Written through `.save()` and verified by RE-READING BOTH FIELDS --
never by the value the save appeared to accept.

IPN vs SKU, and this is the pack rule applied rather than a new idea:
the vendor SKU is `PG03V2-US16A-ESP-2`, where the trailing `-2` is the PACK,
not the product. Stock is counted in PIECES, so the PART's IPN is the piece
identity `PG03V2-US16A-ESP` and the 2-pack lives on the SUPPLIER PART as the
SKU plus pack_quantity=2. Putting the pack marker in the IPN would have made
the part itself a two-pack, which is the "if a part NAME says 10 pack while its
quantity counts pieces, the name is the bug" line in CLAUDE.md.

CATEGORY: flat `Modules` (#22), by precedent not taste. The two comparable
smart plugs already here are both in it -- #389 THIRDREALITY ZigBee Smart Plug
and #484 Z-Wave Dimmer Plug. Rejected: `Electrical` (#71, 2 parts, and these
are network devices rather than building electrical), `Electronics/Power`
(#54 -- a documented shadow root where the flat side usually wins), and a new
`Smart Home` root (14 shadow roots are already open; creating a taxonomy root
on my own judgement is a decision, not transcription).

PRICE: the line is booked at the ITEM price of USD 17.50 per 2-pack unit.
Shipping (USD 9.00 on 54653, USD 12.00 on 56290) is deliberately EXCLUDED from
the line, per the eBay/AliExpress precedent -- folding shipping into the item
price inflates piece cost forever. The asserts reconcile against the ITEM
subtotal, never the order total.

NO LINK AND NO IMAGE on the supplier part. The exact product URL was not
verified live and is not derivable from the SKU the way an eBay item id is, and
`harvest-image-at-part-creation` is an OPEN decision item, not approved. An
invented URL is worse than an empty field.

MANUFACTURER: is_manufacturer=True, by precedent rather than taste. Athom makes
the boards it sells, which is the same shape as Pololu -- the one comparable
direct-from-maker vendor here -- and Pololu carries is_manufacturer=True. No
ManufacturerPart is created (not asked for, and the SKU is already the identity);
the flag only records that this vendor IS the maker, which matters the moment a
second source for the same plug turns up.

54653 is created PLACED here and RECEIVED by the second script. 56290 is
created PLACED and STAYS PLACED -- it shipped 2026-09-21 and is in transit.
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
from stock.models import StockLocation  # noqa: E402

VENDOR = "Athom Tech"
WEBSITE = "https://www.athom.tech"

SKU = "PG03V2-US16A-ESP-2"        # vendor SKU: the trailing -2 is the PACK
IPN = "PG03V2-US16A-ESP"          # piece identity, pack marker stripped
PACK = "2"                        # pcs 2PACKS -- one unit is two plugs
UNIT = "17.50"                    # per 2-pack unit, shipping excluded

NAME = "Athom US V2 Smart Plug 16A, ESPHome pre-flashed (PG03V2-US16A-ESP)"
DESC = "orig: US V2 Plug Made For ESPHome -- 16 A US smart plug, ESPHome pre-flashed"
KEYWORDS = ("Athom, AthomTech, PG03V2, PG03V2-US16A-ESP, ESPHome, smart plug, "
            "smart outlet, 16A, 16 amp, WiFi, Home Assistant, HA, energy "
            "monitoring, power monitoring, US plug, NEMA 5-15, ESP32, "
            "preflashed, pre-flashed, IoT, home automation")

ORDERS = [
    # (vendor order, issue date, qty units, item subtotal, shipping, receive later?)
    ("54653", datetime.date(2026, 8, 17), 3, 52.50, 9.00, True),
    ("56290", datetime.date(2026, 9, 20), 5, 87.50, 12.00, False),
]

IN_SERVICE = "In Service - HA devices"

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

# ------------------------------------------------------------------ preflight
print("=" * 70)
print("PREFLIGHT")
print("=" * 70)

for order, _, qty, sub, ship, _ in ORDERS:
    dup = PurchaseOrder.objects.filter(Q(supplier_reference=order) | Q(reference=order))
    if dup.exists():
        sys.exit(f"!! PO already exists for {order}: {[p.reference for p in dup]}")
    total = float(UNIT) * qty
    print(f"  {order}: {qty} units x ${UNIT} = ${total:.2f} vs stated subtotal "
          f"${sub:.2f}  (+${ship:.2f} shipping, EXCLUDED from the line)")
    assert abs(total - sub) < 0.005, f"{order} line does not reconcile -- refusing"
    print(f"           = {qty * int(PACK)} PIECES at "
          f"${total / (qty * int(PACK)):.2f} each")

dupes = (Part.objects.filter(name__icontains="athom")
         | Part.objects.filter(name__icontains="pg03")
         | Part.objects.filter(IPN=IPN)
         | Part.objects.filter(name__icontains="esphome")).distinct()
print(f"  duplicate scan: {dupes.count()} near matches")
for d in dupes:
    print(f"    #{d.pk} active={d.active} {d.name[:60]}")
    if d.IPN == IPN:
        sys.exit(f"!! part #{d.pk} already carries IPN {IPN} -- resolve by hand")

assert len(NAME) <= 100, f"name too long: {len(NAME)}"
assert len(KEYWORDS) <= 250, f"keywords too long: {len(KEYWORDS)}"
print(f"  name {len(NAME)} chars, keywords {len(KEYWORDS)} chars -- both within limit")

cat = PartCategory.objects.get(pk=22)
assert cat.pathstring == "Modules", f"category moved: {cat.pathstring}"
print(f"  category: #{cat.pk} {cat.pathstring} ({cat.parts.count()} parts)")

sln = StockLocation.objects.get(pk=1)
assert sln.pathstring == "SLN", f"SLN root moved: {sln.pathstring}"
print(f"  SLN root: #{sln.pk} {sln.pathstring} ({sln.children.count()} children)")
if StockLocation.objects.filter(name=IN_SERVICE).exists():
    sys.exit(f"!! a location named {IN_SERVICE!r} already exists")

existing = Company.objects.filter(Q(name__icontains="athom") | Q(website__icontains="athom"))
if existing.exists():
    sys.exit(f"!! Athom company already exists: {[c.name for c in existing]}")
print("  no Athom company exists -- will create")
print("  supplier-flag convention on comparable vendors:")
for nm in ("Pololu", "Seeed", "eBay", "Shars"):
    c = Company.objects.filter(name=nm).first()
    if c:
        print(f"    {c.name:<10} supplier={c.is_supplier} manufacturer={c.is_manufacturer} "
              f"customer={c.is_customer}")

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --commit")

# ------------------------------------------------------------------- company
print()
print("=" * 70)
print("WRITES")
print("=" * 70)

co = Company(
    name=VENDOR,
    description="AthomTech, Shenzhen -- ESPHome pre-flashed smart home hardware",
    website=WEBSITE,
    is_supplier=True,
    is_manufacturer=True,
    is_customer=False,
    notes=("Created 2026-09-22 from decision item `athom-tech-new-vendor`, "
           "approved by Scott the same day.\n\n"
           "Direct-from-vendor Shenzhen supplier of ESPHome pre-flashed smart "
           "home hardware. Orders are placed on athom.tech and PAID VIA PAYPAL, "
           "which is why the sender that surfaced in the order sweep was "
           "paypal.com and not the vendor -- a PayPal receipt is a payment "
           "rail, not a vendor, and the sweep suppressed it as such for two "
           "days running. athom.tech is now on the itemised-vendor list in the "
           "daytime sweep task file so its own confirmations are searched "
           "directly.\n\n"
           "is_manufacturer=True by precedent: Athom makes the boards it "
           "sells, the same shape as Pololu, which is the one comparable "
           "direct-from-maker vendor here and carries the same flag. No "
           "ManufacturerPart exists -- the vendor SKU is already the identity "
           "-- but the flag records that this vendor IS the maker, which is "
           "what matters the moment a second source for the same plug appears "
           "and the two have to be told apart."),
)
co.save()
co.refresh_from_db()
assert co.name == VENDOR, "company name did not stick"
assert co.is_supplier, "is_supplier did not stick"
print(f"  CREATED company #{co.pk} {co.name}  supplier={co.is_supplier}  {co.website}")

# ---------------------------------------------------------------------- part
part = Part(
    name=NAME,
    description=DESC,
    category=cat,
    IPN=IPN,
    keywords=KEYWORDS,
    component=True,
    purchaseable=True,
    assembly=False,
    notes=("Athom 16 A US smart plug, shipped with ESPHome already flashed, so "
           "it adopts straight into Home Assistant with no vendor cloud and no "
           "re-flashing jig.\n\n"
           "COUNTED IN PIECES -- one piece is ONE PLUG. The vendor sells them "
           "in TWO-PACKS: the order line reads `pcs 2PACKS` and the USD 17.50 "
           "unit is two plugs, USD 8.75 each. That pack lives on the SUPPLIER "
           "PART as pack_quantity=2, never on this part and never in the name. "
           "The vendor SKU PG03V2-US16A-ESP-2 carries the same pack marker in "
           "its trailing -2; this part's IPN strips it, because the IPN is the "
           "identity of one plug.\n\n"
           "WHERE EACH ONE IS INSTALLED IS NOT TRACKED HERE, deliberately. "
           "Home Assistant already holds which plug runs what, keyed by the "
           "ESPHome hostname Scott chose at adoption, and it is live and "
           "self-updating. An InvenTree room map would be a hand-copy that can "
           "only ever be more stale than HA. If per-device tracking is ever "
           "wanted the join key is that hostname and the mechanism is "
           "serialisation or belongs_to -- worth it only for gear that does "
           "not move, and a plug moves outlet to outlet in 30 seconds.\n\n"
           "Category is flat Modules by precedent with the two smart plugs "
           "already here, #389 THIRDREALITY ZigBee and #484 Z-Wave Dimmer. See "
           "the script header for what was rejected and why.\n\n"
           "Created 2026-09-22 from decision item `athom-tech-new-vendor`."),
)
part.save()
part.refresh_from_db()
assert part.name == NAME, "part name did not stick"
assert part.IPN == IPN, "IPN did not stick"
assert part.category_id == cat.pk, "category did not stick"
assert part.keywords == KEYWORDS, "keywords did not stick"
print(f"  CREATED part #{part.pk} {part.name}")
print(f"          IPN={part.IPN}  cat={part.category.pathstring}")

# ------------------------------------------------------------- supplier part
sp = SupplierPart(supplier=co, part=part, SKU=SKU,
                  description="2-pack. One unit = two plugs.")
sp.pack_quantity = PACK           # .save() -> clean() -> pack_quantity_native
sp.save()
sp.refresh_from_db()
# Verify BOTH halves by re-read. The text field is what every screen shows;
# pack_quantity_native is the only one receive_po.py actually reads.
assert str(sp.pack_quantity) == PACK, f"pack text did not stick: {sp.pack_quantity!r}"
assert float(sp.pack_quantity_native) == float(PACK), \
    f"pack_quantity_native did not stick: {sp.pack_quantity_native!r}"
print(f"  CREATED sp #{sp.pk} SKU={sp.SKU}")
print(f"          pack_quantity={sp.pack_quantity}  "
      f"pack_quantity_native={sp.pack_quantity_native}  <-- BOTH verified by re-read")

# ------------------------------------------------------------------ location
loc = StockLocation(
    name=IN_SERVICE,
    parent=sln,
    description=("IN SERVICE -- deployed HA devices, NOT spares. Do not pick "
                 "from this location."),
    notes=("Created 2026-09-22 from decision item "
           "`in-service-bucket-for-portable-devices`, approved by Scott "
           "2026-09-20.\n\n"
           "WHAT GOES HERE: small network/HA devices that are DEPLOYED and in "
           "use, but that move without anyone doing paperwork. A smart plug "
           "moves outlet to outlet in 30 seconds and nobody will ever record "
           "it, so per-room rows would be a snapshot that decays silently. "
           "This bucket is one level coarser than the room locations it sits "
           "beside (the nanoHD/PO-0175 convention) and extends that rule "
           "rather than competing with it. The test is not size or value: it "
           "is whether the thing moves without paperwork.\n\n"
           "THIS LOCATION IS NEVER A default_location. A part's "
           "default_location is where a SPARE goes home; stock here is already "
           "in service and must not be picked for a build or a repair. Stock "
           "rows here carry their own do-not-pick note.\n\n"
           "WHICH device is doing WHAT is not recorded here and is not meant "
           "to be -- Home Assistant holds that, live, keyed by ESPHome "
           "hostname. See the notes on the part."),
)
loc.save()
loc.refresh_from_db()
assert loc.parent_id == sln.pk, "location parent did not stick"
assert loc.pathstring == f"SLN/{IN_SERVICE}", f"pathstring wrong: {loc.pathstring}"
print(f"  CREATED location #{loc.pk} {loc.pathstring}")

# --------------------------------------------------------------------- POs
made = []
for order, issue, qty, sub, ship, receive_later in ORDERS:
    ref = PurchaseOrder.generate_reference()
    tail = ("This order is RECEIVED by athom_receive_0922.py -- the goods are "
            "physically in the building and have been since August."
            if receive_later else
            "PLACED and IN TRANSIT -- shipped 2026-09-21. Do NOT receive it "
            "until the goods land and a human checks them in.")
    po = PurchaseOrder(
        supplier=co,
        reference=ref,
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
               f"PACK: one unit is a TWO-PACK, so {qty} units = "
               f"{qty * int(PACK)} plugs at USD "
               f"{sub / (qty * int(PACK)):.2f} each. The supplier part carries "
               "pack_quantity=2; receiving this order at pack 1 would book "
               f"{qty} plugs instead of {qty * int(PACK)}.\n\n"
               "PAID VIA PAYPAL, which is why this order surfaced to the sweep "
               "as a paypal.com sender and not as athom.tech, and why it sat "
               "unimported behind an unknown-vendor decision for two days.\n\n"
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
        notes=(f"{qty} x 2-pack at USD {UNIT} per pack = {qty * int(PACK)} "
               f"plugs. Shipping USD {ship:.2f} excluded."))
    li.save()
    li.refresh_from_db()
    assert float(li.purchase_price.amount) == float(UNIT), \
        f"price did not stick: {li.purchase_price}"

    booked = sum(float(l.purchase_price.amount) * float(l.quantity)
                 for l in po.lines.all())
    assert abs(booked - sub) < 0.005, f"{po.reference} booked total drifted"
    print(f"  CREATED {po.reference} supplier_ref={po.supplier_reference} "
          f"ref_int={po.reference_int} status=PLACED")
    print(f"          line qty={li.quantity} @ {li.purchase_price}  "
          f"booked=${booked:.2f} (subtotal ${sub:.2f})")
    made.append(po)

print()
print("=" * 70)
print("DONE")
print("=" * 70)
print(f"  company  #{co.pk}  {co.name}")
print(f"  part     #{part.pk}  IPN={part.IPN}")
print(f"  sp       #{sp.pk}  SKU={sp.SKU}  pack={sp.pack_quantity} "
      f"native={sp.pack_quantity_native}")
print(f"  location #{loc.pk}  {loc.pathstring}")
for po in made:
    print(f"  {po.reference}  {po.supplier_reference}  {po.lines.count()} line(s)")
print()
print("  NOT DONE HERE, and both need a fact only Scott has:")
print("    - receive PO-0180 (6 pieces) and split 4 in-service / 2 spare")
print("    - part.default_location = the spares location")
