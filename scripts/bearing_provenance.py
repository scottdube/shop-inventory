"""Attach real purchase provenance to the bearings, and fix three wrong names.

Read out of Scott's Amazon order history 2026-08-26 (Chrome, logged in), because
NONE of these purchases exist in InvenTree: Amazon coverage here starts
2025-07-22 and is only continuous from 2026-06-28, while every bearing in this
bin was bought between 2021 and 2024. The parts were invisible to the system,
which is why "why are there five boxes" could not be answered from the database.

THREE NAMES WERE WRONG, and all three in the same direction — a single-seal
suffix on a double-sealed bearing:

  608RS   -> 608-2RS    50 PCS 608-2RS Skateboard Bearing, 2024-09-28
  6803RS  -> 6803-2RS   uxcell 6803-2RS 10pcs, 2024-01-01
  R6RS    -> R6-2RS     10 Pack R6-2RS, 2022-06-01

That matters twice over. A 2RS is sealed BOTH sides, so the drag and the
sealing are not what a single-seal part would give. And for the inch R-series
the seals change the DIMENSION: R6 open is 3/8 x 7/8 x 7/32, R6-2RS is
3/8 x 7/8 x 9/32. The bin's own record had 7/32, from the open-bearing table.
The listing says 9/32 and the listing is describing what is in the bag.
"""
import argparse, os, sys, django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from stock.models import StockItem

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

# part_pk -> (new_name or None, provenance text, stock-note addendum or None)
WORK = {
    1119: ("Ball Bearing 608-2RS, 8 x 22 x 7 mm",
        "PURCHASED 2026-08-26 finding: Amazon, ordered **2024-09-28**, "
        "'50 PCS 608-2RS Skateboard Bearing, 8x22x7, Sealed'.\n\n"
        "NAME CORRECTED from 608RS to 608-2RS: sealed BOTH sides, not one. "
        "Scott's reading of '608RS' off the part was the shorthand, not the "
        "designation.",
        "Bought as 50 on 2024-09-28; 49 counted 2026-08-26, so ONE has been "
        "used in two years."),
    1120: (None,
        "PURCHASED 2026-08-26 finding: Amazon, ordered **2021-01-10**, "
        "'FaGoBearing Pack of 20 608 ZZ Skateboard Bearings, Sackorange 608zz "
        "Double Shielded, 8x22x7'. Double shielded confirms ZZ.",
        "Bought as 20 on 2021-01-10; 13 counted 2026-08-26, so SEVEN used over "
        "five years. The most-consumed bearing in the bin."),
    1121: (None,
        "PURCHASED 2026-08-26 finding: TWO Amazon orders, nine days apart:\n"
        "  2022-11-10  XiKe, '2 Pcs 6203-2RS Double Rubber Seal 17x40x12mm'\n"
        "  2022-11-19  **Timken 6203-2RSC3** 6203-2RS 17x40x12mm\n\n"
        "The second is a TIMKEN and the first is not. If one of the two in hand "
        "is the Timken it is the better bearing and worth identifying before "
        "either gets used on something that matters — check the outer race "
        "marking. C3 also means an INTERNAL CLEARANCE greater than standard, "
        "which is what you want on a press fit or a hot shaft and wrong for a "
        "loose fit.",
        "Two counted 2026-08-26 against two orders totalling 3 pieces "
        "(XiKe 2 + Timken 1), so at least one has been used or the Timken is "
        "elsewhere. Which of the two is which is NOT established."),
    1122: ("Ball Bearing 6803-2RS, 17 x 26 x 5 mm",
        "PURCHASED 2026-08-26 finding: Amazon, ordered **2024-01-01**, "
        "'uxcell 6803-2RS Deep Groove Ball Bearings 17mm x 26mm x 5mm Double "
        "Sealed Chrome Steel P6(ABEC3) 10pcs'.\n\n"
        "NAME CORRECTED from 6803RS to 6803-2RS. P6/ABEC3 precision class.",
        "Bought as 10 on 2024-01-01; 9 counted 2026-08-26, so ONE used."),
    1123: ("Ball Bearing R6-2RS, 3/8 x 7/8 x 9/32 in",
        "PURCHASED 2026-08-26 finding: Amazon, ordered **2022-06-01**, "
        "'10 Pack R6-2RS Ball Bearings, 3/8\" x 7/8\" x 9/32\" Double Rubber "
        "Sealed'.\n\n"
        "NAME AND WIDTH CORRECTED. Was recorded as R6RS at 7/32 wide, which is "
        "the OPEN R6 dimension taken from a standards table. **The sealed "
        "R6-2RS is 9/32 (7.14 mm) wide** — the seals add width. Scott's "
        "measurement of 0.875 OD x 0.375 bore was right and confirmed the "
        "series; nobody measured the WIDTH, which is the one the table got "
        "wrong.",
        "Bought as 10 on 2022-06-01; 8 counted 2026-08-26, so TWO used."),
    1124: (None,
        "PURCHASED 2026-08-26 finding: Amazon order **111-9180031-3026635**, "
        "ordered **2022-12-11**, seller **Dr.Bearing**, $19.99, paid from gift "
        "card balance.\n\n"
        "ONE unit of a listing titled '2 Sets'. The line total equals the unit "
        "price, so this is 2 sets and not 5 of anything — the '5 boxes' in the "
        "group are five DIFFERENT items, not five of these.",
        "LABEL FIGURE CONFIRMED against the order: 1 x '2 Sets' = 2 sets = "
        "2 cones + 2 cups. Still no physical count; the [ESTIMATE] stands until "
        "somebody opens the bag and sees four pieces."),
    1117: (None,
        "PURCHASED 2026-08-26 finding: **TWO** Amazon orders, three days apart:\n"
        "  2024-01-07  '[2 Pack] MGN9 200mm Linear Sliding Rail Guide with 2pcs "
        "MGN9H Linear Bearing Sliding Carriage Block'\n"
        "  2024-01-10  the same listing again\n\n"
        "So **FOUR rails and four blocks were bought**, and two rails are in "
        "hand. The other two are unaccounted for — used, or still somewhere on "
        "the wire shelves.\n\n"
        "Both open questions on this part are now ANSWERED by the listing:\n"
        "  - LENGTH is 200 mm exactly. Scott's eye estimate was right.\n"
        "  - BLOCK IS **MGN9H**, the long carriage — not MGN9C. Higher load "
        "rating and a different mounting-hole pattern than the short block.",
        None),
}

for pk, (newname, prov, snote) in WORK.items():
    p = Part.objects.get(pk=pk)
    print(f"[{pk}] {p.name[:60]}" + (f"\n      -> {newname}" if newname else ""))

if not a.commit:
    print("\nDRY RUN -- add --commit")
    sys.exit()

for pk, (newname, prov, snote) in WORK.items():
    p = Part.objects.get(pk=pk)
    if newname and p.name != newname:
        # .save(), not .update(): the pathstring lesson. Any field a model
        # derives in save() is stale after a queryset write, and it is cheaper
        # to always use save() on a name than to audit which models derive what.
        p.name = newname
        p.save()
        p.refresh_from_db()
    if "PURCHASED 2026-08-26 finding" not in (p.notes or ""):
        Part.objects.filter(pk=pk).update(notes=(p.notes or "").rstrip() + "\n\n" + prov)
    if snote:
        si = StockItem.objects.filter(part_id=pk).first()
        if si and "2026-08-26 finding" not in (si.notes or ""):
            StockItem.objects.filter(pk=si.pk).update(
                notes=(si.notes or "").rstrip() + "\n\nPURCHASE HISTORY, 2026-08-26 finding: " + snote)

print("\nverify:")
for pk in WORK:
    p = Part.objects.get(pk=pk)
    q = sum(float(s.quantity) for s in StockItem.objects.filter(part=p))
    print(f"  [{pk}] {q:>4g} x {p.name}")
