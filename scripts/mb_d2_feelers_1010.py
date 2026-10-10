"""MB-D2 "grey folding tool" answered by Scott's close-up, 2026-10-10: two feeler
gauges, photographed on the red VINCA caliper case in D2. Nothing on file
(feeler, thickness gage/gauge, 25025, RB-FG, cornwell, oem tools: 0 hits).

Named from the stamps only -- OEM Tools 25025 and Cornwell-Allied RB-FG-10.
Blade count and range are not stamped on the faces shown; not guessed.

    itq run scripts/mb_d2_feelers_1010.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
MEAS = PartCategory.objects.get(pk=47); assert MEAS.pathstring == "Tooling/Measuring"
D2 = StockLocation.objects.get(name="MB-D2", parent__pk=381)
SRC = "Filed 2026-10-10 from Scott's close-up photo of Metrology Bench drawer 2."
NEW = [
    ("OEM Tools 25025 Feeler Gauge",
     "Feeler gauge, straight blades, knurled pivot nut",
     "feeler gauge, feeler gage, thickness gauge, OEM Tools, OEMTOOLS, 25025",
     "Case stamped 'OEM TOOLS 25025'. Blade count and range not read."),
    ("Cornwell-Allied RB-FG-10 Feeler Gauge",
     "Feeler gauge, offset/narrow blades, knurled pivot nut, made in USA",
     "feeler gauge, feeler gage, thickness gauge, Cornwell, Allied, RB-FG-10",
     "Case stamped 'RB-FG-10 CORNWELL-ALLIED MADE IN U.S.A.'. Blade count and range not read."),
]
for name, *_ in NEW:
    ex = Part.objects.filter(name=name).first()
    print(f"{'EXISTS' if ex else 'CREATE'} {name}" + (f" (#{ex.pk})" if ex else ""))
if not COMMIT:
    sys.exit("\nDRY RUN -- add --commit")

for name, desc, kw, note in NEW:
    p = Part.objects.filter(name=name).first()
    if not p:
        p = Part(name=name, description=desc, keywords=kw, category=MEAS, component=False,
                 purchaseable=True, assembly=False, default_location=D2,
                 notes=f"{SRC} {note}\n\nPurchase history unknown; no PO, no price.")
        p.save(); p.refresh_from_db()
        assert p.category_id == MEAS.pk and p.default_location_id == D2.pk
    if not StockItem.objects.filter(part=p).exists():
        s = StockItem(part=p, location=D2, quantity=1, notes=SRC + " One seen.")
        s.save(); s.refresh_from_db()
        assert s.location_id == D2.pk
        print(f"CREATED part #{p.pk} SI #{s.pk}: {name}")
