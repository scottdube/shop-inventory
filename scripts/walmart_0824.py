"""Decision queue item 6: the two Walmart orders of 2026-08-22.

Scott logged Browser 1 into walmart.com on 2026-08-24, so both order-details
pages were readable and neither PO is a stub.

  #2000151-54121530  Sterilite Set of (10) 6 Quart Storage Bins, clear, snap
                     lids, white. Walmart item 5297809753. 1 item.
                     Subtotal $10.98, Tax $0.00, Total $10.98.

  #2000151-82176030  TWO IDENTICAL Akro-Mils 24 Drawer Plastic Cabinets,
                     yellow. Walmart item 5540399890. Shipped as two separate
                     1-item parcels, which is why the email read "+ 1 item"
                     and the second item looked unidentified.
                     Subtotal $99.98, Tax $0.00, Total $99.98.

TWO price traps on these orders, both avoided:

1. The Sterilite email said "You saved a total of $6.99", which reads as an
   item discount. It is not - the order page shows it as a WAIVED $35-order-
   minimum delivery fee (Walmart+). The item really is $10.98.

2. The Akro-Mils unit price is $49.99, DERIVED as $99.98 / 2, not read
   verbatim. That is the sanctioned move for an extended price over identical
   units (the task file says exactly this for Shars/Tormach/Pololu/Haas), and
   it is safe here only because tax is $0.00 and there is no shipping line, so
   the subtotal is purely 2 x unit. It is flagged in the PO notes as derived.

Both PLACED, not received. The Akro-Mils parcels had not arrived at the time of
writing (due 08-25).

OPEN QUESTION, deliberately not decided here: a 24-drawer cabinet may belong in
InvenTree as LOCATIONS (bin-wall drawers, ^[AB][1-3]-R\\d+C\\d+$) rather than
only as a part. Creating the PO records the purchase and its cost either way;
creating the drawer locations is a separate act for when Scott installs them,
and the bin-wall is the interactive drawer walk's territory. Noted on the part.
"""
import argparse
import datetime
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart          # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from order.status_codes import PurchaseOrderStatus        # noqa: E402
from part.models import Part, PartCategory                # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()
DRY = not a.commit

WALMART = Company.objects.filter(name="Walmart").first()
assert WALMART, "Walmart Company missing - run add_walmart.py first"
CAT = PartCategory.objects.get(pk=89)   # Shop/Accessories
assert CAT.pathstring == "Shop/Accessories", CAT.pathstring
print(f"supplier={WALMART}  category={CAT.pathstring}")

PARTS = {
    "5297809753": dict(
        name="Storage Bins, 6 Quart, clear, snap-on lid - 10 pack",
        description=("Sterilite 6-quart clear plastic storage bins with white snap-on lids, "
                     "sold as a set of 10. Shop small-parts storage. "
                     "orig: Sterilite Set of (10) 6 Quart Small Storage Bins, Clear Plastic "
                     "Storage Containers with Snap-on Lids, White"),
        keywords=("storage bin, storage bins, tote, totes, container, containers, "
                  "6 quart, snap lid, Sterilite, clear bin, small parts storage"),
    ),
    "5540399890": dict(
        name="Parts Cabinet, 24-Drawer, plastic, yellow - Akro-Mils",
        description=("Akro-Mils 24-drawer plastic parts cabinet, yellow, for hardware and "
                     "small parts. NOTE: may belong in InvenTree as LOCATIONS (bin-wall "
                     "drawers) as well as a part - not decided as of 2026-08-24. "
                     "orig: Akro-Mils 24 Drawer Plastic Cabinet Storage Organizer with "
                     "Drawers for Hardware, Small Parts, Craft Supplies, Yellow"),
        keywords=("parts cabinet, drawer cabinet, storage organizer, 24 drawer, "
                  "Akro-Mils, small parts, hardware organizer, bin wall, drawer unit"),
    ),
}

ORDERS = [
    dict(order="2000151-54121530", date="2026-08-22",
         desc="Walmart order 2000151-54121530 - Sterilite 6qt storage bins, 10-pack",
         notes=("Created 2026-08-24 from the Walmart order-details page (Browser 1 signed in).\n"
                "Subtotal $10.98, Tax $0.00, Total $10.98 - price read verbatim.\n"
                "The email's 'You saved a total of $6.99' is a WAIVED $35-order-minimum\n"
                "delivery fee (Walmart+), NOT an item discount. The item is $10.98.\n"
                "Delivered 2026-08-23. PLACED, not received."),
         lines=[("5297809753", 1, "10.98")]),
    dict(order="2000151-82176030", date="2026-08-22",
         desc="Walmart order 2000151-82176030 - 2x Akro-Mils 24-drawer parts cabinet",
         notes=("Created 2026-08-24 from the Walmart order-details page (Browser 1 signed in).\n"
                "TWO IDENTICAL cabinets, shipped as two separate 1-item parcels - which is why\n"
                "the order email read '+ 1 item' and the second item looked unidentified.\n"
                "Subtotal $99.98, Tax $0.00, Total $99.98.\n"
                "UNIT PRICE $49.99 IS DERIVED ($99.98 / 2), not read verbatim. Safe here only\n"
                "because tax is $0.00 and there is no shipping line, so subtotal = 2 x unit.\n"
                "FedEx 537730901931, due 2026-08-25. PLACED, not received."),
         lines=[("5540399890", 2, "49.99")]),
]


def supplierpart(item_id):
    sp = SupplierPart.objects.filter(supplier=WALMART, SKU=item_id).first()
    if sp:
        print(f"    reorder: {item_id} -> part #{sp.part.pk}")
        return sp
    spec = PARTS[item_id]
    dupe = Part.objects.filter(name=spec["name"]).first() or Part.objects.filter(IPN=item_id).first()
    if dupe:
        print(f"    dedup: {item_id} -> existing part #{dupe.pk}")
        part = dupe
    elif DRY:
        print(f"    ~ WOULD create part {spec['name']!r}")
        return None
    else:
        part = Part.objects.create(
            name=spec["name"], description=spec["description"][:250], category=CAT,
            IPN=item_id, keywords=spec["keywords"],
            active=True, purchaseable=True, component=False,
        )
        assert Part.objects.get(pk=part.pk).name == spec["name"], "part write did not stick"
        print(f"    + part #{part.pk} {part.name[:55]}")
    if DRY:
        return None
    return SupplierPart.objects.create(
        part=part, supplier=WALMART, SKU=item_id,
        link=f"https://www.walmart.com/ip/{item_id}")


for o in ORDERS:
    print(f"\n=== {o['order']} ===")
    if (PurchaseOrder.objects.filter(supplier_reference=o["order"]).first()
            or PurchaseOrder.objects.filter(reference=o["order"]).first()):
        print("  SKIP (exists)")
        continue
    if DRY:
        for iid, qty, unit in o["lines"]:
            print(f"  ~ WOULD create PO line {iid} qty={qty} unit=${unit}")
            supplierpart(iid)
        continue
    po = PurchaseOrder.objects.create(
        supplier=WALMART, reference=PurchaseOrder.generate_reference(),
        supplier_reference=o["order"], description=o["desc"][:250], notes=o["notes"],
        issue_date=datetime.date.fromisoformat(o["date"]),
        status=PurchaseOrderStatus.PLACED.value)
    fresh = PurchaseOrder.objects.get(pk=po.pk)
    print(f"  + {fresh.reference} supplier_ref={fresh.supplier_reference} "
          f"status={fresh.get_status_display()} reference_int={fresh.reference_int}")
    for iid, qty, unit in o["lines"]:
        sp = supplierpart(iid)
        li = PurchaseOrderLineItem.objects.create(
            order=po, part=sp, quantity=qty,
            purchase_price=unit, purchase_price_currency="USD",
            notes=("Walmart item %s; unit price from the order-details page." % iid)
                  + (" DERIVED as subtotal/qty over identical units." if qty > 1 else ""))
        print(f"    line: {iid} qty={qty} unit=${unit} (pk {li.pk})")
    print(f"  lines={po.lines.count()} status={po.get_status_display()} (no stock created)")

print("\nDRY RUN - nothing written" if DRY else "\ncommitted")
