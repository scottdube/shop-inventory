"""Hakko USA order 1000204070 (2026-11-05 16:30 PT) -> new vendor, 6 new parts, PO.

Scott placed this order himself on 2026-11-05. It is the LRD soldering station
(see memory electronics-bench-tools-by-site): the FX-951 he wanted a second of
was discontinued April 2025, so this is the FX-971 kit, plus five T39 tips
picked for the work done here (0.5 mm LGA/QFN SMD, 0603/0805, through-hole kits).

PRICE SOURCE: the "Your American Hakko Products order confirmation" email,
itemised per line, qty 1 each:

    FX971-010   FX-971 Soldering Station (kit: station + FX-9701 iron + holder)  $329.97
    T39-BC2535  Bevel tip 2.5 mm                                                  $17.97
    T39-BL02    Conical tip 0.2 mm, long                                          $16.57
    T39-D12     Chisel tip 1.2 mm                                                 $15.77
    T39-D16     Chisel tip 1.6 mm                                                 $15.77
    T39-KU      Knife tip                                                         $27.17
    HGC059-L    Free gift shirt                                                    $0.00
    Subtotal $423.22  Shipping $0.00  Tax $0.00  Total $423.22 (PayPal)

The shirt is not shop inventory and gets no line; the PO note records it.
No sales tax was charged although it ships to Florida (Florida use tax is
Scott's to settle, not InvenTree's).

NEW VENDOR, created with Scott's explicit OK ("Yes, record it", 2026-11-05).
That is the approval the unknown-vendor rule asks for; the domain also goes into
vendor_registry.json in the same commit so the sweep sees later Hakko orders.
Named "American Hakko Products" because that is the legal name on the email and
the site footer; "Hakko USA" goes in the description so a search on either finds it.

KIT AS ONE PART, not station + iron + holder. Scott bought it as one SKU, and
the pieces are not stocked separately. Rejected splitting: three rows to keep
consistent for something that moves as one. Split later if an FX-9701 is
ever bought on its own.

CATEGORIES copied from the nearest existing rows: station like #314
(Equipment/Soldering), tips like the T15 set #333 (Consumables/Solder).

PLACED, ship-to LRD (1879 Lake Ridge Dr), FedEx Ground, no ETA in the email.
Receive with receive_po.py when it arrives.

    itq run scripts/po_1105_hakko_1000204070.py [--commit]
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

ORDER = "1000204070"
ISSUE = datetime.date(2026, 11, 5)
SUBTOTAL = TOTAL = 423.22
VENDOR = "American Hakko Products"
SITE = "https://hakkousa.com"

TIP_KW = "soldering tip, solder tip, T39, Hakko, FX-971, FX-9701, FX-972"
LINES = [
    dict(sku="FX971-010", unit="329.97", cat_from=314, cat_path="Equipment/Soldering",
         url="fx-9701-standard-kit.html",
         name="Hakko FX-971 Soldering Station kit (FX971-010)",
         desc="Hakko FX-971 station + FX-9701 iron + holder, as sold in kit FX971-010. Takes T39 tips. No tips in the box.",
         kw="soldering station, soldering iron, Hakko, FX-971, FX971, FX971-010, FX-9701, T39, LRD bench",
         dupe=["FX-971", "FX971", "FX-9701"],
         notes=("Bought for the LRD bench 2026-11-05 (Hakko USA order 1000204070). "
                "Successor to the FX-951 (discontinued April 2025); T15 tips do NOT fit. "
                "Sleep sensor is in the FX-9701 handpiece, so the holder is passive.")),
    dict(sku="T39-BC2535", unit="17.97", url="t39-bc2535-bevel-tip.html",
         name="Hakko T39-BC2535 Bevel Tip 2.5 mm (FX-971)",
         desc="Hakko T39 bevel soldering tip, 2.5 mm. For FX-9701 / FX-971.",
         kw=TIP_KW + ", bevel, BC2535, drag soldering, QFN", dupe=["BC2535"],
         notes="Picked for drag-soldering QFN/fine-pitch and big pads. Hakko USA order 1000204070."),
    dict(sku="T39-BL02", unit="16.57", url="t39-bl02-conical-tip.html",
         name="Hakko T39-BL02 Conical Tip 0.2 mm long (FX-971)",
         desc="Hakko T39 long conical soldering tip, 0.2 mm. For FX-9701 / FX-971.",
         kw=TIP_KW + ", conical, fine, BL02, 0.5 mm pitch, LGA", dupe=["BL02"],
         notes="Picked for touch-up under the microscope and 0.5 mm pitch. Hakko USA order 1000204070."),
    dict(sku="T39-D12", unit="15.77", url="t39-d12-chisel-tip.html",
         name="Hakko T39-D12 Chisel Tip 1.2 mm (FX-971)",
         desc="Hakko T39 chisel soldering tip, 1.2 mm. For FX-9701 / FX-971.",
         kw=TIP_KW + ", chisel, D12, 0402, 0603", dupe=["T39-D12"],
         notes="Picked for 0402/0603 and QFN side pads. Hakko USA order 1000204070."),
    dict(sku="T39-D16", unit="15.77", url="t39-d16-chisel-tip.html",
         name="Hakko T39-D16 Chisel Tip 1.6 mm (FX-971)",
         desc="Hakko T39 chisel soldering tip, 1.6 mm. For FX-9701 / FX-971.",
         kw=TIP_KW + ", chisel, D16, general purpose, through-hole", dupe=["T39-D16"],
         notes="The everyday tip: through-hole kits, 0805/0603. Hakko USA order 1000204070."),
    dict(sku="T39-KU", unit="27.17", url="t39-ku-knife-tip.html",
         name="Hakko T39-KU Knife Tip (FX-971)",
         desc="Hakko T39 knife soldering tip (KU). For FX-9701 / FX-971.",
         kw=TIP_KW + ", knife, KU, drag soldering, bridges", dupe=["T39-KU"],
         notes="Picked for drag-soldering pin rows and clearing bridges. Hakko USA order 1000204070."),
]
TIP_CAT_FROM, TIP_CAT_PATH = 333, "Consumables/Solder"

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

# ---------------------------------------------------------------- idempotency
if PurchaseOrder.objects.filter(Q(supplier_reference=ORDER) | Q(reference=ORDER)).exists():
    sys.exit(f"!! PO already exists for {ORDER} — nothing to do")
if Company.objects.filter(Q(name__icontains="hakko") | Q(website__icontains="hakkousa")).exists():
    sys.exit("!! a Hakko company already exists — resolve by hand")

total = 0.0
for ln in LINES:
    q = Q()
    for t in ln["dupe"]:
        q |= Q(name__icontains=t) | Q(IPN__icontains=t) | Q(keywords__icontains=t)
    d = Part.objects.filter(q).distinct()
    if d.exists():
        sys.exit(f"!! possible dupe for {ln['sku']}: {list(d.values_list('pk', 'name'))}")
    src = ln.get("cat_from", TIP_CAT_FROM)
    path = ln.get("cat_path", TIP_CAT_PATH)
    cat = Part.objects.get(pk=src).category
    assert cat.pathstring == path, f"category moved: {cat.pathstring}"
    assert len(ln["name"]) <= 100 and len(ln["kw"]) <= 250 and len(ln["desc"]) <= 250, ln["sku"]
    total += float(ln["unit"])
    print(f"  NEW {ln['sku']:<11} {cat.pathstring:<20} ${ln['unit']:>7}  {ln['name']}")

print(f"reconcile: lines ${total:.2f} vs email subtotal ${SUBTOTAL:.2f}")
assert abs(total - SUBTOTAL) < 0.005, "lines do not reconcile — refusing"
print(f"WOULD create company '{VENDOR}' and PO {PurchaseOrder.generate_reference()}")

if not args.commit:
    raise SystemExit("\nDRY RUN — add --commit")

# ---------------------------------------------------------------- vendor
co = Company(name=VENDOR, description="Hakko USA (hakkousa.com), Valencia CA — Hakko's US arm",
             website=SITE, email="websupport@hakkousa.com", phone="800-88-HAKKO",
             is_supplier=True, is_manufacturer=True, is_customer=False, currency="USD")
co.save()
co.refresh_from_db()
assert co.name == VENDOR and co.is_supplier, "company did not stick"
print(f"CREATED company #{co.pk} {co.name}")

# ---------------------------------------------------------------- PO
po = PurchaseOrder(
    supplier=co, reference=PurchaseOrder.generate_reference(), supplier_reference=ORDER,
    description="Hakko FX-971 kit + 5 T39 tips (LRD bench)",
    issue_date=ISSUE, status=PurchaseOrderStatus.PLACED.value)
po.save()
note_set(po, ("Placed by Scott 2026-11-05 on hakkousa.com; recorded the same evening at his OK.\n\n"
              "PRICE SOURCE: the order-confirmation email, itemised, qty 1 each. Subtotal $423.22, "
              "shipping $0, tax $0 (none charged although ship-to is Florida), total $423.22, PayPal.\n\n"
              "Also in the box: a free Hakko shirt (HGC059-L, $0) — not shop inventory, no line.\n\n"
              "Ships to LRD, 1879 Lake Ridge Dr, FedEx Ground. TARGET DATE empty: no ETA in the email.\n\n"
              "T39-D24 was wanted but backordered at Hakko USA, so it was left off.\n\n"
              "PLACED, not received. Receive with receive_po.py when it arrives."))
po.refresh_from_db()
assert note_text(po).startswith("Placed by Scott"), "PO note did not stick"
assert po.status == PurchaseOrderStatus.PLACED.value and po.supplier_reference == ORDER
assert po.reference != ORDER, "vendor number leaked into reference"
print(f"CREATED {po.reference} supplier_ref={po.supplier_reference}")

for ln in LINES:
    cat = Part.objects.get(pk=ln.get("cat_from", TIP_CAT_FROM)).category
    is_station = ln["sku"] == "FX971-010"
    part = Part(name=ln["name"], description=ln["desc"], category=cat, IPN=ln["sku"],
                keywords=ln["kw"], component=not is_station, purchaseable=True,
                assembly=False, link=f"{SITE}/{ln['url']}")
    part.save()
    note_set(part, ln["notes"])
    part.refresh_from_db()
    assert part.name == ln["name"] and part.category_id == cat.pk and part.IPN == ln["sku"]
    assert note_text(part) == ln["notes"], "part note did not stick"

    sp = SupplierPart(supplier=co, part=part, SKU=ln["sku"], link=f"{SITE}/{ln['url']}")
    sp.pack_quantity = "1"            # .save() -> clean() -> pack_quantity_native
    sp.save()
    sp.refresh_from_db()
    assert float(sp.pack_quantity_native) == 1.0, f"pack native: {sp.pack_quantity_native}"

    li = PurchaseOrderLineItem(order=po, part=sp, quantity=1, purchase_price=ln["unit"],
                               purchase_price_currency="USD",
                               notes=f"Line price from the Hakko order email: 1 x ${ln['unit']}.")
    li.save()
    li.refresh_from_db()
    assert float(li.purchase_price.amount) == float(ln["unit"]), "price did not stick"
    print(f"  part #{part.pk} sp #{sp.pk} line {li.quantity:g} @ {li.purchase_price}  {part.name}")

po.refresh_from_db()
booked = sum(float(l.purchase_price.amount) * float(l.quantity) for l in po.lines.all())
ok = po.lines.count() == len(LINES) and abs(booked - SUBTOTAL) < 0.005
print(f"\n{po.reference} lines={po.lines.count()} booked=${booked:.2f} (email ${SUBTOTAL:.2f})")
print("VERDICT:", "SUCCESS" if ok else "FAILED")
