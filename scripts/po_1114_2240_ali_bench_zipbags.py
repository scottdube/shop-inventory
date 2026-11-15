"""Queue C, 22:40 daytime sweep 2026-11-14: seven orders -> seven PLACED POs.

All placed 2026-11-14, all ship to The Villages FL (LRD). Prices are the ITEM LINES on the
order-details pages read in the agent Chrome 2026-11-14 22:4x, never the order totals.

  AliExpress (Company #10), one PO per order number (Scott's ruling 2026-08-28), eta 11-27:
  order              seller                   item                                  unit x qty  total
  8216790551625753   CCHT Store               polyimide (Kapton) tape 25mm x 33m     3.99 x1    4.27
  8216790551645753   CCHT Store               polyimide (Kapton) tape 12mm x 33m     1.78 x1    1.90
  8216790551705753   FreeBoom Electric Store  polyimide tape 5mm x 33m               2.32 x1    2.48
  8216790551665753   China DIYPHONE Store     MECHANIC TP01 ESD alcohol pump bottle  3.69 x1    3.95
  8216790551685753   China DIYPHONE Store     MaAnt MY-065 nano cleaning sponge      2.81 x2    6.01
  8216790551725753   Etall Global Store       KAISI anti-static cloth 9x9, 200pcs    6.85 x2   14.66
  Total - subtotal is shipping/tax, not on the line.

  Amazon 113-9557005-2032210: Aubeco 120 pcs 6x9in clear zip bags 2 mil, ASIN B09M9VXXN1,
  item line 11.59 x1, tax 0.81, grand total 0.00 (gift card 12.40) -- not a price.

Packs: tape rolls, the bottle and the sponge count as themselves (pack 1). The cloth variant is
200 identical cloths -> pack 200. The zip bags are 120 identical bags -> pack 120 (the
2026-11-09 zipbag_pack_400_1109 ruling: stock counts bags, the supplier part carries the pack).

Dry run (default) prints duplicate candidates across name/description/keywords/IPN/SKU and
categories; fill REUSE/CAT, then --commit. PLACED, never received, no stock created.
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

RUN = "22:40 daytime sweep 2026-11-14"
PLACED = datetime.date(2026, 11, 14)
ALI_ETA = datetime.date(2026, 11, 27)

ITEMS = {
    "kapton25": dict(
        name="Tape Polyimide (Kapton) 25mm x 33m",
        desc=("orig: 1PCS 5-25MM X 33M Professional Heat Resistant High Temperature Insulation "
              "Electronics Industry Welding Polyimide Kapton Tape | variant: 1pcs Green, 25mm"),
        kw="kapton, polyimide, tape, high temperature, heat resistant, insulation, masking, 25mm, 33m",
        notes="Polyimide (Kapton-type) high-temperature tape, 25 mm wide, 33 m roll. Stock counts ROLLS.",
        pack="1", terms=["kapton", "polyimide"], cat_terms=["tape", "adhesive", "consum"]),
    "kapton12": dict(
        name="Tape Polyimide (Kapton) 12mm x 33m",
        desc=("orig: 1PCS 5-25MM X 33M Professional Heat Resistant High Temperature Insulation "
              "Electronics Industry Welding Polyimide Kapton Tape | variant: Brown, 1PCS, 12mm"),
        kw="kapton, polyimide, tape, high temperature, heat resistant, insulation, masking, 12mm, 33m",
        notes="Polyimide (Kapton-type) high-temperature tape, 12 mm wide, 33 m roll. Stock counts ROLLS.",
        pack="1", terms=["kapton", "polyimide"], cat_terms=["tape"]),
    "kapton5": dict(
        name="Tape Polyimide (Kapton) 5mm x 33m",
        desc=("orig: High Temperature Heat BGA Tape Thermal Insulation Tape Polyimide Adhesive "
              "Insulating Adhesive Tape 3D Printing Board Protection | variant: 1 roll, 33m per "
              "roll, 5mm, China Mainland"),
        kw="kapton, polyimide, tape, high temperature, BGA, heat resistant, insulation, masking, 5mm, 33m",
        notes="Polyimide (Kapton-type) high-temperature tape, 5 mm wide, 33 m roll. Stock counts ROLLS.",
        pack="1", terms=["kapton", "polyimide"], cat_terms=["tape"]),
    "pumpbottle": dict(
        name="Bottle Pump Dispenser ESD 180ml (IPA) MECHANIC TP01",
        desc=("orig: MECHANIC Anti-static Alcohol Liquid Bottle Press Pumping ESD Fluid Dispenser "
              "Plastic Container for Motherboard PCB Cleaning Tool 180ML TP01"),
        kw=("dispenser, pump bottle, alcohol, IPA, isopropyl, ESD, anti-static, flux cleaning, "
            "180ml, MECHANIC, TP01"),
        notes="Anti-static press-pump dispenser bottle, 180 ml, for IPA / flux remover. Stock counts bottles.",
        pack="1", terms=["dispenser", "pump bottle", "tp01"], cat_terms=["clean", "consum", "solder"]),
    "sponge": dict(
        name="Sponge Cleaning Nano PCB/Screen MaAnt MY-065",
        desc=("orig: MaAnt MY-065 Nano Cleaning Spong No Residue for Phone Screen PCB Motherboard "
              "Back Glass Camera Solder Flux Oil Frame Clean Tool | variant: MaAnt MY-065"),
        kw="sponge, nano sponge, cleaning, PCB, flux, screen, no residue, MaAnt, MY-065",
        notes=("MaAnt MY-065 no-residue nano cleaning sponge for PCBs and screens. Pieces per "
               "listing unit NOT confirmed from the page; pack 1 until the box is opened."),
        pack="1", terms=["sponge", "my-065"], cat_terms=["clean"]),
    "esdcloth": dict(
        name="Cloth Cleaning Anti-Static Lint-Free 9x9cm KAISI",
        desc=("orig: KAISI 50pcs 200pcs Anti Static LCD Cleaning Cloth 9*9 Lint Free Polyester "
              "Cleanroom Dust-free Cloth Phone LCD Screen Repair Tool | variant: 200pcs"),
        kw="cloth, wipe, lint free, anti-static, ESD, cleanroom, dust-free, polyester, 9x9, KAISI",
        notes=("KAISI 9 x 9 cm lint-free polyester cleanroom cloths. Listing variant is 200 "
               "identical cloths -> pack 200; stock counts cloths."),
        pack="200", terms=["lint", "cleanroom", "kaisi"], cat_terms=["clean"]),
    "zip6x9": dict(
        name="Bag Zip Clear 6x9in 2mil",
        desc=('orig: Aubeco 120Pcs 6"x9" Clear Plastic Zip Bags, 2 Mil Thick | Multi Purpose '
              "Resealable Storage Bag for Jewelry, Small Items, Packaging, Travel, Home, Office, "
              "Organization"),
        kw="zip bag, ziplock, resealable, bag, clear, 6x9, 2 mil, packaging, Aubeco",
        notes=("Aubeco clear resealable zip bags, 6 x 9 in, 2 mil. Listing is 120 identical bags "
               "-> pack 120; stock counts bags."),
        pack="120", terms=["zip bag", "aubeco", "6x9"], cat_terms=["bag", "packag"]),
}

# vendor, order, key, sku, qty, unit, money, seller
ORDERS = [
    ("ali", "8216790551625753", "kapton25", "8216790551625753/1pcs Green, 25mm", 1, "3.99",
     "item 3.99 x1, subtotal 3.99, total 4.27", "CCHT Store"),
    ("ali", "8216790551645753", "kapton12", "8216790551645753/Brown, 1PCS, 12mm", 1, "1.78",
     "item 1.78 x1, subtotal 1.78, total 1.90", "CCHT Store"),
    ("ali", "8216790551705753", "kapton5", "8216790551705753/1 roll, 33m per roll, 5mm", 1, "2.32",
     "item 2.32 x1, subtotal 2.32, total 2.48", "FreeBoom Electric Store"),
    ("ali", "8216790551665753", "pumpbottle", "8216790551665753/MECHANIC TP01 180ML", 1, "3.69",
     "item 3.69 x1, subtotal 3.69, total 3.95", "China DIYPHONE Store"),
    ("ali", "8216790551685753", "sponge", "8216790551685753/MaAnt MY-065", 2, "2.81",
     "item 2.81 x2, subtotal 5.62, total 6.01", "China DIYPHONE Store"),
    ("ali", "8216790551725753", "esdcloth", "8216790551725753/200pcs", 2, "6.85",
     "item 6.85 x2, subtotal 13.70, total 14.66", "Etall Global Store"),
    ("amazon", "113-9557005-2032210", "zip6x9", "B09M9VXXN1", 1, "11.59",
     "item line 11.59, tax 0.81, grand total 0.00 (gift card 12.40 applied, not a price)",
     "Aubeco"),
]

# Filled from the dry run. No reuse: #89/#390 are the ELEGOO 4-width polyimide ASSORTMENT
# (one unit of four rolls), not a single-width roll; #849-851 are other bag sizes; #1489
# Kimwipes is a different product. Categories follow the nearest same-kind parts: tapes with
# #89 and bags with #851 in 28 Consumables (the flat root, per the shadow-roots memory);
# cleaning items with Kimwipes #1489 in 56 Tools/Consumables.
REUSE = {k: None for k in ITEMS}
CAT = {"kapton25": 28, "kapton12": 28, "kapton5": 28, "zip6x9": 28,
       "pumpbottle": 56, "sponge": 56, "esdcloth": 56}
ITEMS["zip6x9"]["name"] = "Zip Bag 6x9 in, clear reclosable, 2 mil"
for k in ("kapton25", "kapton12", "kapton5"):
    ITEMS[k]["notes"] += " Similar: #89 ELEGOO polyimide 4-width assortment."

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
args = ap.parse_args()

ALI = Company.objects.get(pk=10)
AMAZON = Company.objects.get(name="Amazon")
VENDOR = {"ali": ALI, "amazon": AMAZON}

for key, it in ITEMS.items():
    q = Q()
    for t in it["terms"]:
        q |= (Q(name__icontains=t) | Q(description__icontains=t) | Q(keywords__icontains=t)
              | Q(IPN__icontains=t) | Q(supplier_parts__SKU__icontains=t))
    print(f"\n[{key}] part candidates:")
    for c in Part.objects.filter(q).distinct()[:25]:
        sps = [(s.pk, s.supplier.name[:12], s.SKU[:40], str(s.pack_quantity)) for s in c.supplier_parts.all()]
        print(f"  #{c.pk} active={c.active} cat={c.category_id} {c.name!r} | {c.description[:60]!r} sp={sps}")
    cq = Q()
    for t in it["cat_terms"]:
        cq |= Q(name__icontains=t)
    print(f"[{key}] categories: " + "; ".join(f"{c.pk}={c.pathstring}" for c in PartCategory.objects.filter(cq)[:15]))

for _, order, *_ in ORDERS:
    dup = PurchaseOrder.objects.filter(Q(supplier_reference=order) | Q(reference=order))
    print(f"{order}: existing={[(p.reference, p.lines.count()) for p in dup]}")

if not args.commit:
    raise SystemExit("\nDRY RUN -- fill REUSE/CAT, add --commit")

assert all(CAT[k] or REUSE[k] for k in ITEMS), "fill CAT (or REUSE) for every item"


def supplier_part(vendor, key, sku):
    it = ITEMS[key]
    sp = SupplierPart.objects.filter(supplier=vendor, SKU__iexact=sku).first()
    if sp:
        print(f"REUSE sp #{sp.pk} {sku} -> part #{sp.part_id}")
        return sp
    part = Part.objects.get(pk=REUSE[key]) if REUSE[key] else Part.objects.filter(name__iexact=it["name"]).first()
    link = f"https://www.amazon.com/dp/{sku}" if vendor == AMAZON else ""
    if part is None:
        part = Part(name=it["name"], description=it["desc"][:250], keywords=it["kw"],
                    category=PartCategory.objects.get(pk=CAT[key]), link=link,
                    component=True, purchaseable=True, assembly=False)
        part.save()
        part.refresh_from_db()
        assert part.name == it["name"] and part.keywords == it["kw"], "part did not stick"
        note_set(part, it["notes"] + f"\n\nCreated by the queue C daytime sweep, {RUN}.")
        assert note_text(part).startswith(it["notes"][:30]), "part note did not stick"
        print(f"CREATED part #{part.pk} {part.name}")
    else:
        print(f"REUSE part #{part.pk} {part.name}")
    sp = SupplierPart(supplier=vendor, part=part, SKU=sku, link=link, description=it["desc"][:250])
    sp.pack_quantity = it["pack"]
    sp.save()  # .save(), never .update(): only pack_quantity_native is read at receive
    sp.refresh_from_db()
    assert sp.SKU == sku and sp.part_id == part.pk, "sp did not stick"
    assert float(sp.pack_quantity_native) == float(it["pack"]), sp.pack_quantity_native
    print(f"CREATED sp #{sp.pk} {sku} -> part #{part.pk} pack native={sp.pack_quantity_native}")
    return sp


for vkey, order, key, sku, qty, price, money, seller in ORDERS:
    vendor = VENDOR[vkey]
    dup = PurchaseOrder.objects.filter(Q(supplier_reference=order) | Q(reference=order))
    if dup.exists():
        assert dup.count() == 1
        po = dup.first()
        if po.lines.count():
            print(f"SKIP {order}: {po.reference} already has lines")
            continue
        print(f"RESUMING {po.reference} (0 lines)")
    else:
        label = "AliExpress" if vkey == "ali" else "Amazon order"
        po = PurchaseOrder(supplier=vendor, reference=PurchaseOrder.generate_reference(),
                           supplier_reference=order,
                           description=f"{label} {order} — {seller} — {ITEMS[key]['name']} (to The Villages FL)"[:250],
                           issue_date=PLACED,
                           target_date=ALI_ETA if vkey == "ali" else datetime.date(2026, 11, 15),
                           status=PurchaseOrderStatus.PLACED.value)
        po.save()
        po.refresh_from_db()
    assert po.supplier_id == vendor.pk and po.supplier_reference == order
    assert po.status == PurchaseOrderStatus.PLACED.value and po.reference != order
    note_set(po, f"Auto-created by the queue C daytime sweep, {RUN}.\n\nSeller: {seller}. "
                 f"Ships to The Villages FL (LRD).\n\nPrice read verbatim from the order-details "
                 f"page item line: {money}.\n\nItem: {ITEMS[key]['desc'][6:]}\n\n"
                 f"Supplier-part pack {ITEMS[key]['pack']}.\n\nPLACED, not received.")
    assert note_text(po).startswith("Auto-created"), "PO note did not stick"
    sp = supplier_part(vendor, key, sku)
    li = PurchaseOrderLineItem(order=po, part=sp, quantity=qty,
                               purchase_price=price, purchase_price_currency="USD")
    li.save()
    li.refresh_from_db()
    assert float(li.quantity) == qty and float(li.purchase_price.amount) == float(price)
    po.refresh_from_db()
    print(f"CREATED {po.reference} supplier_ref={po.supplier_reference} status={po.status} "
          f"target={po.target_date} lines={po.lines.count()}")
