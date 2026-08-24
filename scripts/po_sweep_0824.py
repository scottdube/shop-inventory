"""Queue C sweep 2026-08-22 -> 2026-08-24: two new Amazon orders.

Prices come from the Amazon ORDER-DETAILS PAGE read in Chrome, never from the
email. Order 113-6309387-8181062 is the exact trap the task file warns about:
Item(s) Subtotal $16.48, Rewards Points -$12.20, Grand Total $4.28. The items
cost $6.99 and $9.49; the grand total is cash-after-points and is not a price.

Reference discipline (learned 2026-08-20, cost a day): the visible reference
comes from generate_reference(), and the vendor order number goes ONLY in
supplier_reference. Writing a raw vendor number into `reference` is what
clamped reference_int to int32 max and broke generate_reference() globally.

Ordered != received: the POs are left PLACED and no stock is created.
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

AMAZON = Company.objects.filter(name__istartswith="Amazon").first()
MATERIALS = PartCategory.objects.filter(name="Materials").first()
PLACED = PurchaseOrderStatus.PLACED.value

print(f"supplier={AMAZON}  category={MATERIALS}")

# New parts to create, keyed by ASIN. Canonical name per rule 1: real component
# identity, seller brand and pack count dropped to the description.
NEW_PARTS = {
    "B09YHWKKTR": dict(
        name="Copper Clad Laminate PCB 150 x 100 x 0.8mm Single-Sided",
        description=(
            "PATIKIL single-sided FR4 copper clad, 150 x 100 x 0.8 mm. Sold in 5-packs. "
            "Distinct from #234 (7x10cm Chanzon) and #789 (7x10cm uxcell) by SIZE - "
            "footprint is part identity, do not merge. "
            "orig: PATIKIL FR4 Single Side Copper Clad Laminate PCB, 5 Pack 150 x 100 x "
            "0.8mm Copper Plated Universal Prototype Circuit Board"),
        keywords=("copper clad, PCB blank, blank PCB, FR4, laminate, single sided, "
                  "prototype board, copper board, PCB stock, 150x100"),
    ),
    "B0922XTTNF": dict(
        name="Acrylic Sheet 12 x 12in, 1/16in thick, clear",
        description=(
            "Outus clear acrylic (PMMA) sheet, 12 x 12 in, 1/16 in (1.6 mm) thick. "
            "Sold in 4-packs. Cast vs extruded NOT verified - the listing says 'cast' "
            "but that is seller copy, and it matters for laser cutting. "
            "orig: Outus 4 Pcs 12 x 12 Inch Clear Acrylic Sheet 1/16 Inch Thick "
            "Transparent Acrylic Sheet Clear Plastic Panel Cast Glass Sheets for DIY "
            "Handcraft Decor Picture Frame Paintings Display Art Craft"),
        keywords=("acrylic, plexiglass, plexiglas, PMMA, perspex, acrylic sheet, "
                  "clear sheet, plastic sheet, laser stock, 1/16 inch"),
    ),
}

ORDERS = [
    dict(
        order="113-6309387-8181062", date="2026-08-24",
        desc="Amazon order 113-6309387-8181062 - copper clad PCB blanks (2 lines)",
        notes=("Auto-created from Amazon order confirmation 2026-08-24.\n"
               "PER-ITEM PRICES READ FROM THE ORDER-DETAILS PAGE IN CHROME, not the email.\n"
               "Item(s) Subtotal $16.48; Rewards Points -$12.20; Grand Total $4.28.\n"
               "The $4.28 grand total is cash-after-points and is NOT an item price.\n"
               "PLACED, not received - receive by hand when the box arrives."),
        lines=[("B01MCVLDDZ", 1, "6.99"), ("B09YHWKKTR", 1, "9.49")],
    ),
    dict(
        order="113-3993148-7168211", date="2026-08-23",
        desc="Amazon order 113-3993148-7168211 - clear acrylic sheet 12x12in",
        notes=("Auto-created from Amazon order confirmation 2026-08-23.\n"
               "Price read from the order-details page in Chrome: Item(s) Subtotal $16.99,\n"
               "no points applied, grand total also $16.99.\n"
               "Classified IN as shop raw material (laser/enclosure stock) despite the\n"
               "listing's craft-decor keywords. PLACED, not received."),
        lines=[("B0922XTTNF", 1, "16.99")],
    ),
]


def get_supplierpart(asin):
    """Find the SupplierPart for an ASIN, creating the Part if it is genuinely new."""
    sp = SupplierPart.objects.filter(supplier=AMAZON, SKU=asin).first()
    if sp:
        print(f"    reorder: {asin} -> part #{sp.part.pk} {sp.part.name[:50]}")
        return sp

    spec = NEW_PARTS.get(asin)
    if not spec:
        print(f"    !! {asin}: no SupplierPart and no spec — line skipped")
        return None

    # Dedup by canonical name and by ASIN in IPN before creating anything.
    dupe = Part.objects.filter(name=spec["name"]).first() or \
        Part.objects.filter(IPN=asin).first()
    if dupe:
        print(f"    dedup: {asin} matched existing part #{dupe.pk} {dupe.name[:45]}")
        part = dupe
    else:
        if not a.commit:
            print(f"    ~ WOULD create part [{spec['name']}] cat={MATERIALS}")
            return None
        part = Part.objects.create(
            name=spec["name"], description=spec["description"][:250],
            category=MATERIALS, IPN=asin, keywords=spec["keywords"],
            active=True, purchaseable=True, component=True,
        )
        fresh = Part.objects.get(pk=part.pk)
        assert fresh.name == spec["name"], "part write did not stick"
        print(f"    + created part #{part.pk} {part.name[:50]}")

    if not a.commit:
        return None
    sp = SupplierPart.objects.create(
        part=part, supplier=AMAZON, SKU=asin,
        link=f"https://www.amazon.com/dp/{asin}",
    )
    print(f"    + SupplierPart {asin} -> part #{part.pk}")
    return sp


for o in ORDERS:
    print(f"\n=== {o['order']} ({o['date']}) ===")
    existing = PurchaseOrder.objects.filter(supplier_reference=o["order"]).first() or \
        PurchaseOrder.objects.filter(reference=o["order"]).first()
    if existing:
        print(f"  SKIP (exists): -> {existing.reference}")
        continue
    if not a.commit:
        print(f"  ~ WOULD create PO, {len(o['lines'])} lines")
        for asin, qty, price in o["lines"]:
            print(f"    line {asin} qty={qty} unit=${price}")
            get_supplierpart(asin)
        continue

    po = PurchaseOrder.objects.create(
        supplier=AMAZON,
        reference=PurchaseOrder.generate_reference(),
        supplier_reference=o["order"],
        description=o["desc"][:250],
        notes=o["notes"],
        issue_date=datetime.date.fromisoformat(o["date"]),
        status=PLACED,
    )
    fresh = PurchaseOrder.objects.get(pk=po.pk)
    print(f"  + {fresh.reference} supplier_ref={fresh.supplier_reference} "
          f"status={fresh.get_status_display()} reference_int={fresh.reference_int}")

    for asin, qty, price in o["lines"]:
        sp = get_supplierpart(asin)
        if not sp:
            continue
        li = PurchaseOrderLineItem.objects.create(
            order=po, part=sp, quantity=qty,
            purchase_price=price, purchase_price_currency="USD",
            notes=f"Amazon {asin}; unit price from the order-details page, not the email.",
        )
        print(f"    line: {asin} qty={qty} unit=${price} (line pk {li.pk})")

    print(f"  lines now={po.lines.count()} status={po.get_status_display()} "
          f"(PLACED - NOT received, no stock created)")

print(f"\nPOs total={PurchaseOrder.objects.count()} parts={Part.objects.count()} "
      f"{'(DRY RUN)' if not a.commit else ''}")
