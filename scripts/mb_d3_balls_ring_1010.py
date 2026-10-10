"""MB-D3 close-ups, 2026-10-10.

  - Ring gauge stamp re-read: "PRG6344-202-1 GO / MTG #5" (the D3 overview had
    been read as PRGEM14-200-1). Size 1.5540 in stays as filed -- Scott points to
    his eBay account, and part #1346 was created from that order's title
    ("Mid Tech Gage 1.5540 Bore Plug Ring Gage"). Stamp added to the notes.
  - Bag of steel balls: PGN Bearings, AISI 52100 chrome steel, 1 in, grade 25,
    label "QUANTITY: 5", FNSKU X001R9LZT9 (an Amazon FBA label). Not in the
    600 pc Breezliy assortment #1142 (that tops out at 1/4 in). CREATE with 5
    taken from the bag label -- card-stated, so [ESTIMATE] until counted.
    Category Hardware, beside #1142, rather than Measuring: it is a bearing
    ball sold as one, whatever it gets used for.

    itq run scripts/mb_d3_balls_ring_1010.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
HW = PartCategory.objects.get(pk=136); assert HW.pathstring == "Hardware"
D3 = StockLocation.objects.get(name="MB-D3", parent__pk=381)
NAME = "PGN Chrome Steel Bearing Ball 1 in, Grade 25"
ring = Part.objects.get(pk=1346); assert "1.5540" in ring.name
print(f"ring #{ring.pk} {ring.name}: add stamp; CREATE {NAME!r} qty 5 in {D3.name}")
if not COMMIT:
    sys.exit("DRY RUN -- add --commit")

if "PRG6344" not in ring.notes:
    Part.objects.filter(pk=1346).update(notes=ring.notes + (
        "\n\nStamped 'PRG6344-202-1 GO' and 'MTG #5' (Scott's close-up, 2026-10-10). "
        "Lives in MB-D3."))
assert "PRG6344" in Part.objects.get(pk=1346).notes

p = Part.objects.filter(name=NAME).first()
if not p:
    p = Part(name=NAME, description="AISI 52100 chrome steel bearing ball, 1 in diameter, grade 25",
             keywords="bearing ball, steel ball, chrome steel, 52100, 1 inch, grade 25, PGN, X001R9LZT9",
             category=HW, component=True, purchaseable=True, assembly=False, default_location=D3,
             notes=("Filed 2026-10-10 from Scott's photo of the bag in Metrology Bench drawer 3. "
                    "Label: PGN Bearings, AISI 52100, diameter 1\", grade 25, quantity 5, "
                    "FNSKU X001R9LZT9 (Amazon). No PO on file, no price."))
    p.save(); p.refresh_from_db()
    assert p.category_id == HW.pk and p.default_location_id == D3.pk
if not StockItem.objects.filter(part=p).exists():
    s = StockItem(part=p, location=D3, quantity=5,
                  notes="[ESTIMATE] 5 per the bag label, not counted by a person.")
    s.save(); s.refresh_from_db(); assert s.location_id == D3.pk and float(s.quantity) == 5
    print(f"CREATED part #{p.pk} SI #{s.pk}: {NAME} x5")
