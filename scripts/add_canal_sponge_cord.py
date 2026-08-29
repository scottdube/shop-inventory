"""Canal Rubber closed-cell neoprene sponge cord, 1/8 and 3/16 in, 100 ft each.

Specs from Scott's own email thread, Canal Rubber, 2025-07-31 (he pointed at it
rather than retyping it):

    "I am interested in your General Purpose of Closed Cell Neoprene Sponge
     Chord is for gasketing material. 1/8" and 3/16" 100' each"
    Marty, Canal Rubber: "Both sizes are in stock. On line prices are not
     correct. Current for 1/8" is $24.84. Current for 3/16" is $37.26"

Paid by phone the same day. Never used. Bought for the vacuum table project,
which is on hold.

THIS IS THE ANSWER TO A REQUIREMENT DERIVED THREE MESSAGES AGO. The uxcell solid
nitrile cord (#1149) was rejected as too rigid for vacuum table gasketing, and
from that failure the specification was written down: closed-cell foam or sponge
cord, soft, low compression force, NOT solid rubber, NOT open-cell. Scott had
already bought exactly that a year earlier and it had never reached the
catalogue. The requirement was real, the answer was on the shelf, and nothing
connected them.

    itq run scripts/add_canal_sponge_cord.py            # dry run
    itq run scripts/add_canal_sponge_cord.py --commit
"""
import argparse, datetime, os, sys, django
from decimal import Decimal

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from company.models import Company, SupplierPart                 # noqa: E402
from part.models import Part                                     # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

BIN, TODAY, FT = "Sealing & Weatherstrip", datetime.date.today(), 100

COMMON = (
 "CLOSED-CELL NEOPRENE SPONGE, and every word of that matters:\n"
 "  SPONGE, not solid — it compresses easily and conforms to a surface that is\n"
 "    not flat. That is the property the solid nitrile cord (#1149) lacked, and\n"
 "    the reason it failed on the vacuum table.\n"
 "  CLOSED-CELL, not open — the cells do not interconnect, so it will not leak\n"
 "    air or wick water THROUGH itself. Open-cell sponge of the same softness\n"
 "    would seal against nothing.\n"
 "  NEOPRENE (CR) — weather, ozone and UV resistant, unlike nitrile. Fine\n"
 "    outdoors and fine on a machine.\n\n"
 "BOUGHT FOR THE VACUUM TABLE PROJECT, which is on hold and has no build order. "
 "Never used. Scott 2026-08-29: \"this is the right stuff to use.\"\n\n"
 "A vacuum table seals under atmospheric pressure alone — roughly 14 psi spread "
 "over the whole surface, very little force at any one point — so the gasket "
 "must do the conforming. Soft closed-cell sponge is the correct answer and "
 "solid cord of any hardness is not; see #1149 for the version that was tried "
 "and eliminated.\n\n"
 "SUPPLIER: Canal Rubber, 329 Canal Street, New York NY 10013, 212-226-7339, "
 "canalrubber.com. Quoted and ordered by email/phone 2025-07-31 — cut to length "
 "and boxed to order, no ASIN and no online cart. Their published web prices "
 "were stated by the vendor to be out of date; the figures here are the ones "
 "quoted in writing that day.")

ITEMS = [
    dict(dia="1/8 in", price=Decimal("24.84"),
         name="Neoprene Sponge Cord, closed-cell, 1/8 in dia (Canal Rubber)"),
    dict(dia="3/16 in", price=Decimal("37.26"),
         name="Neoprene Sponge Cord, closed-cell, 3/16 in dia (Canal Rubber)"),
]

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.get(name=BIN)
existing = Company.objects.filter(name__icontains="canal").first()
print(f"destination {loc.pathstring}")
print(f"supplier 'Canal Rubber': {'exists' if existing else 'WILL BE CREATED'}")
for it in ITEMS:
    print(f"  {it['name'][:62]}  {FT} ft  ${it['price']}/100ft")
    if Part.objects.filter(name=it["name"]).exists():
        sys.exit(f"!! {it['name']!r} already exists")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

canal = existing or Company.objects.create(
    name="Canal Rubber", is_supplier=True, is_customer=False, is_manufacturer=False,
    website="https://www.canalrubber.com",
    description="Rubber and sponge stock, cut to order. 329 Canal St, New York "
                "NY 10013. 212-226-7339. Phone/email ordering only — no online "
                "cart, and the published web prices are not current.")
assert Company.objects.get(pk=canal.pk).is_supplier, "supplier flag did not stick"
print(f"OK  supplier #{canal.pk} {canal.name}")

cat = Part.objects.get(pk=1146).category
for it in ITEMS:
    unit = (it["price"] / Decimal(FT)).quantize(Decimal("0.0001"))
    p = Part.objects.create(
        name=it["name"], category=cat, purchaseable=True, component=True,
        active=True,
        description=(f"Canal Rubber general-purpose closed-cell neoprene sponge "
                     f"cord, {it['dia']} diameter, round. Gasketing material, "
                     f"sold and cut by the foot."))
    Part.objects.filter(pk=p.pk).update(units="ft")
    assert Part.objects.get(pk=p.pk).units == "ft", "units did not stick"
    s = StockItem.objects.create(
        part=p, location=loc, quantity=FT, purchase_price=unit,
        notes=(f"{FT} ft as purchased, NEVER USED (Scott, {TODAY}). Cut to length "
               f"by Canal Rubber 2025-07-31. ${it['price']} for the 100 ft, so "
               f"${unit}/ft."))
    Part.objects.filter(pk=p.pk).update(notes=COMMON, default_location=loc)
    SupplierPart.objects.create(part=p, supplier=canal,
                                SKU=f"Closed Cell Neoprene Sponge Cord {it['dia']}",
                                pack_quantity=str(FT))
    f = StockItem.objects.get(pk=s.pk)
    assert float(f.quantity) == FT and f.location_id == loc.pk, "stock did not stick"
    assert f.stocktake_date is None, "no stocktake — nobody measured the coil"
    booked = Decimal(str(f.purchase_price.amount)) * Decimal(str(f.quantity))
    assert abs(booked - it["price"]) < Decimal("0.02"), \
        f"value wrong: ${booked} vs ${it['price']}"
    print(f"OK  part #{p.pk} stock #{f.pk}  {FT} ft {it['dia']}  "
          f"${unit}/ft, row ${booked}")
