"""Metrology Bench drawers D1-D3 from Scott's photos, 2026-10-10.

Matched first (find_mb_d1_d2_1010.py + a D3 search); almost everything was a
2026-10-05 eBay back-fill row sitting in Unfiled - Machine Shop. Matches MOVE
and the drawer becomes the part's home. Items with no match and a readable
identity are CREATED, qty 1 each (one of each seen; nothing here is a count of
loose pieces). Items whose identity a photo cannot settle are NOT filed -- they
are listed for Scott instead.

Matching notes (field marks read off the photos):
  D1  three Federal faces (one marked C81S, one C3K) = the lot row #1353;
      Mitutoyo 103-135 / 1-2" .0001 / 103-217 frames = the 103-922 set #461;
      black tray with rods + base = 129-132 depth mic #404;
      dial "No. 25-441" on the red printed bracket = #1360;
      blue pouch A-F "5/16 to 6" = Beslands telescoping set #486.
  D2  Starrett S167C #1350; Starrett S829E #1348; VINCA "12in CALIPERS" case
      = DCLA-1205 #251 (DCLA is VINCA's prefix); individual UNC 2B GO/NO-GO
      plugs = #282; "METRIC GO-NO GO PLUG GAUGES" box = #158; ADJUSTABLE
      PARALLEL SETS pouch = #1333.
  D3  wooden box labelled Accusize 0087-2160, 87 pcs, metric grade 2 = #1366;
      ring stamped "PRGEM14-200-1 GO / MTG #5" = Mid Tech ring #1346 (the
      only ring gage on file -- size to confirm).

    itq run scripts/mb_drawers_1010.py            # dry run
    itq run scripts/mb_drawers_1010.py --commit
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
MEAS = PartCategory.objects.get(pk=47); assert MEAS.pathstring == "Tooling/Measuring"
D = {n: StockLocation.objects.get(name=f"MB-D{n}", parent__pk=381) for n in (1, 2, 3)}

# SI pk -> (expected part pk, drawer)
MOVES = {
    1040: (1353, 1), 998: (461, 1), 988: (404, 1), 1047: (1360, 1), 1005: (486, 1),
    1020: (1333, 2), 1037: (1350, 2), 1035: (1348, 2), 956: (251, 2), 963: (282, 2), 934: (158, 2),
    1053: (1366, 3), 1033: (1346, 3),
}
SRC = "Filed 2026-10-10 from Scott's photo of Metrology Bench drawer {d}."
NEW = [
    (1, "Taytools Dial Indicator, blue bezel",
        "Dial indicator, Taytools, blue anodised bezel, lug back",
        "dial indicator, Taytools, indicator",
        "Range and graduation not read from the photo -- read the face."),
    (1, "General Tools Angle-izer",
        "General Tools Angle-izer angle template / protractor with sliding rules",
        "angle-izer, angleizer, protractor, angle gauge, General Tools",
        "Model number not read from the photo."),
    (2, "Tsubosan Hardness Tester Files HRC40-HRC65, 6 pc",
        "File-type hardness testers, HRC40 to HRC65, 6 pc set, made in Japan",
        "hardness tester, hardness file, HRC, Rockwell, Tsubosan",
        "Case reads 'Hardness Tester HRC40-HRC65 6pcs set, TSUBOSAN, Made in Japan'."),
    (2, "Thread Measuring Wire Set, US & Metric, 3-48 TPI (EG06-1002)",
        "Three-wire thread measuring wire set, US and metric, 3 to 48 TPI",
        "thread measuring wires, three wire, 3-wire, pitch diameter, EG06-1002, Accusize",
        "Box label 'EG06-1002 U.S.&Metric Thread Measuring Wires Set, 3 to 48 TPI' "
        "(EG06- is an Accusize prefix; maker not printed on the visible label)."),
    (3, "Gage Block Set, inch (maker and count not read)",
        "Inch gage block set in black fitted case",
        "gage blocks, gauge blocks, inch, metrology",
        "Case carries Scott's 'INCH GAGE BLOCKS' label only. Open it and read the maker, "
        "piece count and grade; rename once."),
    (3, "Pin Gage Set .011-.060 in",
        "Plain pin gages .011 to .060 in, .001 steps, in a numbered black stand",
        "pin gage, pin gauge, plug gage, minus, plus, .011, .060", ""),
    (3, "Pin Gage Set .061-.250 in",
        "Plain pin gages .061 to .250 in, .001 steps, in a numbered black stand",
        "pin gage, pin gauge, plug gage, .061, .250", ""),
    (3, "Pin Gage Set, large (range not read)",
        "Plain pin gages, large sizes, in two black stands",
        "pin gage, pin gauge, plug gage, .251, .500",
        "Likely .251-.500 to continue the .061-.250 set, but the stand numbers were not "
        "legible in the photo -- read them and rename once."),
]

for si, (pp, d) in MOVES.items():
    s = StockItem.objects.select_related("part", "location").get(pk=si)
    assert s.part_id == pp, (si, s.part_id, pp)
    print(f"MOVE SI #{si} {float(s.quantity):g} x {s.part.name[:55]}  {s.location.name} -> {D[d].name}")
for d, name, *_ in NEW:
    ex = Part.objects.filter(name=name).first()
    print(f"{'EXISTS' if ex else 'CREATE'} {D[d].name}: {name}" + (f" (#{ex.pk})" if ex else ""))
if not COMMIT:
    sys.exit("\nDRY RUN -- add --commit")

for si, (pp, d) in MOVES.items():
    StockItem.objects.filter(pk=si).update(location=D[d])
    Part.objects.filter(pk=pp).update(default_location=D[d])
    s = StockItem.objects.get(pk=si)
    assert s.location_id == D[d].pk and Part.objects.get(pk=pp).default_location_id == D[d].pk
print(f"moved {len(MOVES)} rows")

for d, name, desc, kw, note in NEW:
    p = Part.objects.filter(name=name).first()
    if not p:
        assert len(name) <= 100 and len(desc) <= 250 and len(kw) <= 250
        p = Part(name=name, description=desc, keywords=kw, category=MEAS, component=False,
                 purchaseable=True, assembly=False, default_location=D[d],
                 notes=(SRC.format(d=d) + (" " + note if note else "") +
                        "\n\nPurchase history unknown; no PO, no price."))
        p.save(); p.refresh_from_db()
        assert p.category_id == MEAS.pk and p.default_location_id == D[d].pk
    if not StockItem.objects.filter(part=p).exists():
        s = StockItem(part=p, location=D[d], quantity=1, notes=SRC.format(d=d) + " One seen.")
        s.save(); s.refresh_from_db()
        assert s.location_id == D[d].pk
        print(f"CREATED part #{p.pk} SI #{s.pk} @ {D[d].name}: {name}")

for d in (1, 2, 3):
    print(f"\n{D[d].pathstring}:")
    for s in StockItem.objects.filter(location=D[d]).select_related("part").order_by("part__name"):
        print(f"  SI #{s.pk} {float(s.quantity):g} x {s.part.name[:70]}")
