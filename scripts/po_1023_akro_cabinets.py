"""Queue C, 12:40 daytime sweep 2026-10-23: two Amazon orders -> two POs, one line each.

  113-6500689-7543462  placed 2026-10-23, ship to The Villages FL (LRD), "Arriving tomorrow" (10-24)
    1. Akro-Mils 10124 24-drawer plastic storage cabinet, 20x6x16 in, black
                                        B003TV3NL0  sold by Spreetail  $43.99 x1

  113-1423772-1899454  placed 2026-10-23, ship to The Villages FL (LRD), "Arriving tomorrow" (10-24)
    1. Akro-Mils 10164 64-drawer plastic parts cabinet, 20x6x16 in, black
                                        B000LDH3JC  sold by Amazon.com  $50.99 x2
       (the page lists it as two separate shipment rows of $50.99 each; subtotal $101.98 = 2 x 50.99)

Both landed in one confirmation email ("Ordered 3 items: Tool Organizers, Storage & Organization").
Reads as the LRD storage plan (docs/lrd-drawer-walk-2026-10-21/STORAGE-PLAN.md) being bought, but
that is inference -- nothing here assigns them a location.

AMAZON PRICE SOURCE -- the order-details pages, read in Chrome 2026-10-23 12:4x:
  113-6500689-7543462: Item(s) Subtotal $43.99, shipping $0.00, tax $3.08, rewards points
                       -$5.87, Grand Total $41.20.  The $41.20 is NOT a price.
  113-1423772-1899454: Item(s) Subtotal $101.98, shipping $0.00, tax $7.14, Grand Total $109.12.

PACK: each cabinet is one unit (an empty cabinet, not a multipack) -> pack_quantity 1.

Dry run lists existing candidate parts and categories. Pass --c24-cat / --c64-cat <pk>
(or --c24-part / --c64-part <pk> to reuse) and --commit to write. PLACED, never received.
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
from plugins.notes_compat import note_set, note_text  # noqa: E402

# 1.6.1: Part/PO notes are common.Note rows (the template po_1019_* predates the port and
# dies on Part(notes=...)).  The line item keeps a plain CharField only if _meta says so.
LI_HAS_NOTES = any(f.name == "notes" and f.concrete for f in PurchaseOrderLineItem._meta.get_fields())

RUN = "12:40 daytime sweep 2026-10-23"
TODAY = datetime.date(2026, 10, 23)
ARRIVE = datetime.date(2026, 10, 24)

HITS = (Q(name__icontains="akro") | Q(description__icontains="akro")
        | Q(name__icontains="drawer cabinet") | Q(name__icontains="parts cabinet")
        | Q(name__icontains="storage cabinet"))
CATS = (Q(name__icontains="storage") | Q(name__icontains="organi") | Q(name__icontains="cabinet")
        | Q(name__icontains="bin") | Q(name__icontains="shop") | Q(name__icontains="furniture"))

ORDERS = {
    "c24": dict(
        order="113-6500689-7543462",
        asin="B003TV3NL0", price="43.99", qty=1, pack="1", seller="Spreetail",
        subtotal="43.99", tax="3.08", total="41.20", adj="rewards points -$5.87, ",
        name="Parts Cabinet, 24-Drawer, plastic, black - Akro-Mils 10124",
        desc=("orig: Akro-Mils 24-Drawer Plastic Storage Cabinet, 20\" W x 6\" D x 16\" H, Black | "
              "Plastic Cabinet w/ Drawers for Garage Organization, Beads, Building Bricks Storage, "
              "Teacher Toolbox, Makeup, 10124; Amazon B003TV3NL0"),
        kw=("drawer cabinet, parts cabinet, storage cabinet, small parts storage, organizer, "
            "Akro-Mils, Akro, 10124, 24 drawer, plastic drawers, wall mount, bench storage, "
            "hardware storage"),
        sp_desc="Akro-Mils 10124 24-drawer plastic storage cabinet, black",
        notes=("Akro-Mils 10124: 24-drawer plastic small-parts cabinet, 20 in W x 6 in D x 16 in H, "
               "black frame. Same cabinet as part #1090 in black; kept a separate part because "
               "#1090 is the yellow variant. One cabinet -> pack_quantity 1."),
        po_desc="Amazon order 113-6500689-7543462 — Akro-Mils 10124 24-drawer cabinet (to The Villages FL)",
    ),
    "c64": dict(
        order="113-1423772-1899454",
        asin="B000LDH3JC", price="50.99", qty=2, pack="1", seller="Amazon.com",
        subtotal="101.98", tax="7.14", total="109.12", adj="",
        name="Parts Cabinet, 64-Drawer, plastic, black - Akro-Mils 10164",
        desc=("orig: Akro-Mils 10164, 64 Drawer Plastic Parts Storage Hardware and Craft Cabinet, "
              "20-Inch W x 6-Inch D x 16-Inch H, Black; Amazon B000LDH3JC"),
        kw=("drawer cabinet, parts cabinet, storage cabinet, small parts storage, organizer, "
            "Akro-Mils, Akro, 10164, 64 drawer, plastic drawers, wall mount, bench storage, "
            "hardware storage"),
        sp_desc="Akro-Mils 10164 64-drawer plastic parts cabinet, black",
        notes=("Akro-Mils 10164: 64-drawer plastic small-parts cabinet, 20 in W x 6 in D x 16 in H, "
               "black frame. One cabinet -> pack_quantity 1."),
        po_desc="Amazon order 113-1423772-1899454 — 2x Akro-Mils 10164 64-drawer cabinet (to The Villages FL)",
    ),
}

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--c24-cat", type=int)
ap.add_argument("--c24-part", type=int)
ap.add_argument("--c64-cat", type=int)
ap.add_argument("--c64-part", type=int)
args = ap.parse_args()

amazon = Company.objects.get(name="Amazon")

# ------------------------------------------------------------ checks
for key, L in ORDERS.items():
    dup = PurchaseOrder.objects.filter(Q(supplier_reference=L["order"]) | Q(reference=L["order"]))
    if dup.exists():
        sys.exit(f"!! PO already exists for {L['order']}: {[p.reference for p in dup]}")
    assert len(L["kw"]) <= 250 and len(L["name"]) <= 100 and len(L["desc"]) <= 250, \
        (key, len(L["kw"]), len(L["name"]), len(L["desc"]))
    print(f"--- {key}: {L['name']}")
    sp = SupplierPart.objects.filter(SKU__iexact=L["asin"]).first()
    if sp:
        print(f"  supplier part {L['asin']} already exists: sp #{sp.pk} -> part #{sp.part_id}")
    for h in Part.objects.filter(HITS | Q(description__icontains=L["asin"])
                                 | Q(IPN__icontains=L["asin"][-6:]))[:40]:
        print(f"  candidate part #{h.pk}: {h.name}  active={h.active}  cat={h.category_id}: {h.category}")
print("  categories:")
for c in PartCategory.objects.filter(CATS):
    print(f"    {c.pk}: {c.pathstring}  ({c.parts.count()} parts)")

if not args.commit:
    raise SystemExit("\nDRY RUN -- add --c24-cat/--c64-cat <pk> (or --*-part <pk>) --commit")


def build(key, L, cat_pk, part_pk):
    sp = SupplierPart.objects.filter(SKU__iexact=L["asin"]).first()
    if sp:
        print(f"REUSING sp #{sp.pk} part #{sp.part_id}")
    else:
        if part_pk:
            part = Part.objects.get(pk=part_pk)
            print(f"REUSING part #{part.pk} {part.name}")
        else:
            assert cat_pk, f"need --{key}-cat or --{key}-part"
            cat = PartCategory.objects.get(pk=cat_pk)
            part = Part(name=L["name"], description=L["desc"], category=cat, keywords=L["kw"],
                        component=False, purchaseable=True, assembly=False)
            part.save()
            part.refresh_from_db()
            assert part.name == L["name"] and part.category_id == cat.pk and part.keywords == L["kw"]
            note_set(part, L["notes"] + f"\n\nOrdered 2026-10-23 to The Villages FL (LRD), "
                           f"Amazon {L['order']}.\n\nCreated by the queue C daytime sweep, {RUN}.")
            assert note_text(part).startswith(L["notes"][:30]), "part note did not stick"
            print(f"CREATED part #{part.pk} {part.name}  cat={part.category.pathstring}")
        sp = SupplierPart(supplier=amazon, part=part, SKU=L["asin"],
                          link=f"https://www.amazon.com/dp/{L['asin']}", description=L["sp_desc"])
        sp.pack_quantity = L["pack"]
        sp.save()
        sp.refresh_from_db()
        assert sp.SKU == L["asin"] and sp.part_id == part.pk, "sp did not stick"
        assert float(sp.pack_quantity_native) == float(L["pack"]), \
            f"pack native {sp.pack_quantity_native} != {L['pack']}"
        print(f"  sp #{sp.pk}  pack_quantity={sp.pack_quantity} native={sp.pack_quantity_native}")

    po = PurchaseOrder(
        supplier=amazon,
        reference=PurchaseOrder.generate_reference(),
        supplier_reference=L["order"],
        description=L["po_desc"],
        issue_date=TODAY, target_date=ARRIVE,
        status=PurchaseOrderStatus.PLACED.value,
    )
    po.save()
    po.refresh_from_db()
    assert po.status == PurchaseOrderStatus.PLACED.value
    assert po.supplier_reference == L["order"] and po.reference != L["order"]
    note_set(po, (f"Auto-created by the queue C daytime sweep, {RUN}.\n\n"
                  "Ships to The Villages FL (LRD).\n\n"
                  f"PRICE SOURCE: the order-details page — ${L['price']} each x{L['qty']}. "
                  f"Item(s) Subtotal ${L['subtotal']}, shipping $0.00, tax ${L['tax']}, "
                  f"{L['adj']}Grand Total ${L['total']}.\n\n"
                  f"The ${L['total']} grand total is not a price and is deliberately not on the "
                  "line.\n\nPLACED, not received."))
    assert note_text(po).startswith("Auto-created"), "PO note did not stick"
    li_note = (f"Per-item price from the Amazon order-details page (${L['price']}, sold by "
               f"{L['seller']}), NOT the ${L['total']} grand total.")
    li = PurchaseOrderLineItem(
        order=po, part=sp, quantity=L["qty"],
        purchase_price=L["price"], purchase_price_currency="USD")
    if LI_HAS_NOTES:
        li.notes = li_note
    li.save()
    if not LI_HAS_NOTES:
        note_set(li, li_note)
    li.refresh_from_db()
    assert float(li.purchase_price.amount) == float(L["price"]), li.purchase_price
    assert float(li.quantity) == float(L["qty"]), li.quantity
    print(f"  line: sp #{sp.pk} qty {li.quantity} @ {li.purchase_price}")
    po.refresh_from_db()
    print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
          f"target={po.target_date} lines={po.lines.count()}")


build("c24", ORDERS["c24"], args.c24_cat, args.c24_part)
build("c64", ORDERS["c64"], args.c64_cat, args.c64_part)
