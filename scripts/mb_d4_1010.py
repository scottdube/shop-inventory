"""Metrology Bench drawer D4 from Scott's photo, 2026-10-10 (plus a second photo
of the Edge Technology case open).

The D4 search found nothing on file for any of these (knipex, pliers wrench, edge
tech, pro tram, tram, co-ax, coaxial, jd21, 1-2-3, 123 block, 2-4-6, 246 block --
only unrelated hits). The sine bar in the same photo is already SI #1109 in MB-D4.

Counts: the case items and each plier are one of each, as elsewhere. The blocks
are discrete and in plain view (2 big blocks; 4 small in two green printed
holders), so the photo count is recorded but flagged [ESTIMATE] -- a person
confirms it. Rejected: one "pair" part per set, because the shelf question is
"how many blocks", and 1-2-3 blocks are used singly as often as paired.

Knipex: two handles read 86 03 180 and 86 03 250. The third is visibly smaller
and its handle print is not legible; it is filed without a size rather than
guessed as 86 03 125 / 150. Rename once when read.

    itq run scripts/mb_d4_1010.py            # dry run
    itq run scripts/mb_d4_1010.py --commit
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
CAT = {k: PartCategory.objects.get(pk=pk) for k, pk in
       (("meas", 47), ("hand", 40), ("work", 46))}
assert CAT["meas"].pathstring == "Tooling/Measuring"
assert CAT["hand"].pathstring == "Equipment/Hand Tools"
assert CAT["work"].pathstring == "Tooling/Workholding"
D4 = StockLocation.objects.get(name="MB-D4", parent__pk=381)
SRC = "Filed 2026-10-10 from Scott's photo of Metrology Bench drawer 4."
EST = " [ESTIMATE] {n} seen in the photo, not counted by a person -- confirm."

# (category, qty, name, description, keywords, part note, stock note)
NEW = [
    ("meas", 1, "Edge Technology Pro Tram System",
        "Spindle tramming fixture with two 0-0.25 in, .0005 in dial indicators, in fitted case",
        "tram, tramming, Pro Tram, Edge Technology, spindle alignment, indicator",
        "Case opened in a second photo: two indicators, 0-0.25 in, .0005 in grads.",
        " One seen."),
    ("meas", 1, "Accusize Co-Ax Indicator 0-0.15 in (JD21-0001)",
        "Coaxial centering indicator, 0-0.15 in, in black case",
        "co-ax, coax, coaxial indicator, centering indicator, centring, JD21-0001, Accusize",
        "Case label 'JD21-0001 CO-AX Indicator, 0-0.15\"'.", " One seen."),
    ("work", 2, "2-4-6 Block",
        "Ground steel 2 x 4 x 6 in setup block, tapped and through holes",
        "2-4-6 block, 246 block, setup block, riser, workholding",
        "Maker unknown, no PO.", EST.format(n=2)),
    ("work", 4, "1-2-3 Block",
        "Ground steel 1 x 2 x 3 in setup block, 23 holes",
        "1-2-3 block, 123 block, setup block, riser, workholding",
        "Stored two to a green 3D-printed holder. Maker unknown, no PO.", EST.format(n=4)),
    ("hand", 1, "Knipex Pliers Wrench 86 03 250, 10 in",
        "Knipex pliers wrench, 250 mm, 52 mm / 2 in capacity, plastic grips",
        "Knipex, pliers wrench, 8603250, 86 03 250, smooth jaw, adjustable",
        "Handle reads '86 03 250 52 mm / 2\"'.", " One seen."),
    ("hand", 1, "Knipex Pliers Wrench 86 03 180, 7 in",
        "Knipex pliers wrench, 180 mm, plastic grips",
        "Knipex, pliers wrench, 8603180, 86 03 180, smooth jaw, adjustable",
        "Handle reads '86 03 180'.", " One seen."),
    ("hand", 1, "Knipex Pliers Wrench, small (size not read)",
        "Knipex pliers wrench, the smallest of three in the drawer, plastic grips",
        "Knipex, pliers wrench, smooth jaw, adjustable, 86 03",
        "Handle print not legible in the photo. Read it and rename once "
        "(86 03 125 or 86 03 150 by size).", " One seen."),
]

for c, q, name, *_ in NEW:
    ex = Part.objects.filter(name=name).first()
    print(f"{'EXISTS' if ex else 'CREATE'} {CAT[c].pathstring} qty {q}: {name}" + (f" (#{ex.pk})" if ex else ""))
if not COMMIT:
    sys.exit("\nDRY RUN -- add --commit")

for c, q, name, desc, kw, note, snote in NEW:
    p = Part.objects.filter(name=name).first()
    if not p:
        assert len(name) <= 100 and len(desc) <= 250 and len(kw) <= 250
        p = Part(name=name, description=desc, keywords=kw, category=CAT[c], component=False,
                 purchaseable=True, assembly=False, default_location=D4,
                 notes=f"{SRC} {note}\n\nPurchase history unknown; no PO, no price.")
        p.save(); p.refresh_from_db()
        assert p.category_id == CAT[c].pk and p.default_location_id == D4.pk
    if not StockItem.objects.filter(part=p).exists():
        s = StockItem(part=p, location=D4, quantity=q, notes=SRC + snote)
        s.save(); s.refresh_from_db()
        assert s.location_id == D4.pk and float(s.quantity) == q
        print(f"CREATED part #{p.pk} SI #{s.pk} qty {q}: {name}")

print(f"\n{D4.pathstring}:")
for s in StockItem.objects.filter(location=D4).select_related("part").order_by("part__name"):
    print(f"  SI #{s.pk} {float(s.quantity):g} x {s.part.name[:70]}")
