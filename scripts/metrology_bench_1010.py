"""Scott 2026-10-10, two photos: "these things need to be inventoried and put
into the metrology bench".

Matched against existing rows first (find_metrology_1010.py), all four were in
Unfiled - Machine Shop or absent:
  - grey-cased combination square, 12 in, iGaging logo on the rule, square +
    protractor + center heads -> part #1336 "Combination Square Set 12in, 4R"
    (SI 1023). The name lacked the maker; iGaging added from the rule.
  - red-cased Starrett Last Word set -> part #1359 711GCS (SI 1046).
  - ground bar in a wooden case -> part #1364 Lathe Alignment Test Bar, 272 mm
    parallel shank (SI 1051), the only test bar on file.
  - drilled steel block (6 holes on top, 4 large through the side): NO match.
    Created with no size in the name -- dimensions were not given and a photo
    does not measure. Rename once when Scott reads them.
All go to SLN/Metrology Bench (pk 381) itself, not a drawer: which drawer was
not said. default_location follows, since Scott named the bench as the home.

    itq run scripts/metrology_bench_1010.py            # dry run
    itq run scripts/metrology_bench_1010.py --commit
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
MB = StockLocation.objects.get(pk=381); assert MB.pathstring == "SLN/Metrology Bench"
MEAS = PartCategory.objects.get(pk=47); assert MEAS.pathstring == "Tooling/Measuring"
MOVES = {1023: 1336, 1046: 1359, 1051: 1364}
for si, pp in MOVES.items():
    s = StockItem.objects.select_related("part", "location").get(pk=si)
    assert s.part_id == pp and float(s.quantity) == 1, (si, s.part_id, s.quantity)
    print(f"SI #{si} {s.part.name[:55]} @ {s.location.pathstring} -> {MB.pathstring}")
blk = Part.objects.filter(name__startswith="Steel Setup Block, drilled").first()
print(f"block part exists: {blk}")
if not COMMIT:
    sys.exit("\nDRY RUN -- add --commit")

for si, pp in MOVES.items():
    StockItem.objects.filter(pk=si).update(location=MB)
    Part.objects.filter(pk=pp).update(default_location=MB)
    s = StockItem.objects.get(pk=si); p = Part.objects.get(pk=pp)
    assert s.location_id == MB.pk and p.default_location_id == MB.pk
    print(f"moved SI #{si}; part #{pp} home = bench")

sq = Part.objects.get(pk=1336)
if "iGaging" not in sq.name:
    Part.objects.filter(pk=1336).update(
        name="iGaging Combination Square Set 12in, 4R",
        keywords=((sq.keywords or "") + ", iGaging, protractor head, center head, square head").strip(", "))
    sq.refresh_from_db(); assert sq.name.startswith("iGaging")
    print(f"part #1336 -> {sq.name}")

if not blk:
    blk = Part(
        name="Steel Setup Block, drilled",
        description="Ground steel block, 6 holes in the top face, 4 large holes through the side",
        keywords="setup block, 1-2-3 block, 2-4-6 block, riser, drilled block, metrology",
        category=MEAS, component=False, purchaseable=True, assembly=False, default_location=MB,
        notes=("Filed 2026-10-10 from Scott's photo of the metrology-bench items. "
               "**Size not recorded** -- a photo does not measure; read it with a "
               "caliper and rename once (e.g. 1-2-3 / 2-4-6). Maker unknown, no PO."))
    blk.save(); blk.refresh_from_db()
    assert blk.category_id == MEAS.pk
    print(f"CREATED part #{blk.pk} {blk.name}")
if not StockItem.objects.filter(part=blk).exists():
    s = StockItem(part=blk, location=MB, quantity=1, notes="One seen in the 2026-10-10 photo.")
    s.save(); s.refresh_from_db()
    assert s.location_id == MB.pk
    print(f"CREATED SI #{s.pk} @ {MB.pathstring}")
