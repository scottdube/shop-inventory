"""T-nut and bearing-ball kits into L1-D2 — INTERIM placement, not a home.

Scott 2026-08-28: "L1D2 for now." The 'for now' is load-bearing, so
default_location is deliberately LEFT EMPTY. docs/CONTEXT.md: default_location
is where a spare goes HOME, never a staging area. Setting it to L1-D2 would
turn a parking spot into a permanent answer, and nobody would ever revisit it.
Homeless shows up on a report; a wrong home does not.

Both quantities are the PRINTED PACK FIGURE, so both are [ESTIMATE] with NO
stocktake_date -- they stay on the never-counted report until somebody tallies
one. The T-nut box is visibly open in the photo, which makes its 120 an upper
bound at best.

    itq run scripts/add_hardware_kits.py            # dry run
    itq run scripts/add_hardware_kits.py --commit
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from company.models import Company, SupplierPart                 # noqa: E402
from part.models import Part, PartCategory                       # noqa: E402
from stock.models import StockItem, StockLocation                # noqa: E402

BIN = "L1-D2"
INTERIM = ("INTERIM PLACEMENT, 2026-08-28 — Scott: \"L1D2 for now.\" This is "
           "where it is, not where it belongs. No default_location is set on "
           "purpose, so the part stays visible as homeless rather than quietly "
           "adopting a parking spot as its home.\n\n")

KITS = [
  dict(name="T-Nut Assortment, 2020 series, 120 pc (M3/M4/M5/M6/M8)",
       cat="Hardware", asin="X001NE1LWJ", qty=120, pack="120",
       desc=("Drop-in / slide-in T-nuts for 2020 aluminium extrusion, assorted "
             "M3 M4 M5 M6 M8, 120 pieces in a compartment box. Made in China."),
       notes=INTERIM +
        "[ESTIMATE] 120 is the PRINTED PACK FIGURE off the box label, not a "
        "count. The box is visibly OPEN in the 2026-08-28 photo with loose nuts "
        "in it, so 120 is an upper bound and probably wrong. No stocktake_date "
        "on purpose — this stays on the never-counted report until somebody "
        "tallies the compartments.\n\n"
        "2020 SERIES MEANS THE EXTRUSION, NOT THE THREAD. It fits 20x20 mm "
        "profile with a 6 mm slot; the M3-M8 range is the thread cut in the "
        "nut. A T-nut for 2020 will not fit 3030 or 4040, and that is the "
        "mistake worth avoiding when grabbing one.\n\n"
        "Amazon ASIN X001NE1LWJ. No purchase order in this system matches it."),
  dict(name="Bearing Ball Assortment, chrome steel, SAE, 600 pc (6 sizes)",
       cat="Hardware", asin=None, qty=600, pack="600",
       desc=("Breezliy SAE precision bearing ball assortment, chrome steel, 600 "
             "pieces: 3/32, 1/8, 5/32, 3/16, 7/32 and 1/4 inch, 100 of each."),
       notes=INTERIM +
        "[ESTIMATE] 600 is the PRINTED PACK FIGURE — six sizes at 100 each, per "
        "the box lid. Nobody counted it and no stocktake_date is set.\n\n"
        "SAE / INCH SIZES, NOT METRIC: 3/32, 1/8, 5/32, 3/16, 7/32, 1/4 in "
        "(2.381, 3.175, 3.969, 4.762, 5.556, 6.350 mm). None of them is a "
        "metric ball. Substituting the nearest metric size into a bearing race "
        "is the failure this note exists to prevent — 1/8 in is 3.175 mm and a "
        "3 mm ball will rattle.\n\n"
        "Chrome steel, so they rust. Not for anything wet or food-adjacent "
        "without checking; stainless would be a different part."),
]

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

loc = StockLocation.objects.get(name__iexact=BIN)
print(f"destination: {loc.pathstring}  — {(loc.description or '(no description)')[:60]}")
for k in KITS:
    print(f"  {k['name'][:60]}  qty {k['qty']} [ESTIMATE], no stocktake")
    if Part.objects.filter(name=k["name"]).exists():
        sys.exit(f"!! {k['name']!r} already exists")
if not a.commit:
    raise SystemExit("\nDRY RUN — add --commit")

amazon = Company.objects.get(name="Amazon", is_supplier=True)
for k in KITS:
    cat = PartCategory.objects.filter(name__iexact=k["cat"]).first()
    p = Part.objects.create(name=k["name"], description=k["desc"], category=cat,
                            purchaseable=True, component=True, active=True)
    s = StockItem.objects.create(part=p, location=loc, quantity=k["qty"],
                                 notes=k["notes"])
    Part.objects.filter(pk=p.pk).update(notes=k["notes"])   # no default_location
    f = StockItem.objects.get(pk=s.pk)
    assert float(f.quantity) == k["qty"] and f.location_id == loc.pk
    assert f.stocktake_date is None, "something stamped a stocktake date"
    assert Part.objects.get(pk=p.pk).default_location_id is None, \
        "default_location was set — L1-D2 is interim, not a home"
    if k["asin"] and not SupplierPart.objects.filter(SKU=k["asin"]).exists():
        SupplierPart.objects.create(part=p, supplier=amazon, SKU=k["asin"],
                                    pack_quantity=k["pack"],
                                    link=f"https://www.amazon.com/dp/{k['asin']}")
    print(f"OK  part #{p.pk}, stock #{f.pk} qty={float(f.quantity):g} — "
          f"no home set, no stocktake")
