"""Enter the LRD bag of Alrhso AA battery contacts into F1-R5C4 as three parts (2026-11-02).

Part 765 models the listing as "10 pairs, each one sprung negative + one flat
positive". Opening a bag shows that's wrong: the listing ("...Negative to
Positive Conversion Spring Contact Plate, 12x11mm, 12x28mm") mixes three
pieces. Scott counted this bag: 9 double (series) plates, 8 spring plates,
7 flat plates. That's 24 pieces, not 20.

The three pieces aren't interchangeable, so each gets its own part and row.
Rejected: one row of 765 counting pieces. "24" can't say whether a cell
position can be built, and the row would need re-reading by kind every time.
765 is left as is (name, unit) for the SLN bag, which is still unopened (stock
67, label line 1-62-200). Its description and a note now say the bag splits
into these three when it is opened. This LRD bag (label line 1-50-B1) is the
2025-12-13 order, which shipped while Scott was in Florida. Bought, not
carried down.

    itq run scripts/battery_contacts_lrd_1102.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from common.models import Note  # noqa: E402
from InvenTree.status_codes import StockHistoryCode  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

commit = "--commit" in sys.argv
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R5C4")
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
p765 = Part.objects.get(pk=765)
SRC = ("Alrhso AA battery contact bag (listing B0FMYDC1ZN, bag X004T1PV1F, label line "
       "1-50-B1), Amazon order 2025-12-13, bought at LRD. Scott counted at put-away 2026-11-02: "
       "9 double + 8 spring + 7 flat. Split from part 765, which models the bag as 10 pairs.")
NEW = [  # name, description, qty
    ("Battery Contact Plate, AA, series link 12x28 mm",
     "Double plate: positive button + negative spring on one strip, joins two AA cells in series", 9),
    ("Battery Contact Plate, AA, negative spring 12x11 mm",
     "Single sprung negative contact with solder tab", 8),
    ("Battery Contact Plate, AA, positive flat 12x11 mm",
     "Single flat positive contact (button) with solder tab", 7),
]
held = StockItem.objects.filter(location=loc)
assert not held.exists(), f"F1-R5C4 holds {list(held.values_list('pk', 'part__name'))}"
for name, _, q in NEW:
    dup = Part.objects.filter(name=name)
    print(f"{q:3} x {name}" + (f"  (part exists: {dup.first().pk})" if dup.exists() else ""))
print("765 category:", p765.category.pathstring, "| SLN stock 67:", StockItem.objects.get(pk=67).quantity)
if not commit:
    raise SystemExit("DRY RUN - add --commit")

made = []
for name, desc, q in NEW:
    p = Part.objects.filter(name=name).first()  # rerun-safe: reuse a part a failed run saved
    if p is None:
        p = Part(name=name, description=desc, category=p765.category, component=True,
                 purchaseable=True, default_location=loc)
        p.save()
        Note.objects.create(content_object=p, title="Source", primary=True,
                            content=f"Sold only inside the Alrhso mixed bag; see part 765. {SRC}")
    s = StockItem(part=p, location=loc, quantity=q)
    s.save()
    Note.objects.create(content_object=s, title="Count", primary=True, content=SRC)
    s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": float(q)}, notes=SRC)
    made.append((p.pk, s.pk, q))

ids = ", ".join(str(m[0]) for m in made)
Part.objects.filter(pk=765).update(description=(
    "Alrhso mixed AA contact bag, sold as '10 pairs'. When opened it splits into three parts: "
    f"series link / negative spring / positive flat ({ids}). The LRD bag held 9 / 8 / 7."))
Note.objects.create(content_object=p765, title="Bag contents", primary=False, content=(
    "<p><strong>2026-11-02: the bag isn't 10 pairs.</strong> The LRD bag, opened and counted by "
    "Scott, held 9 double (series) plates, 8 spring plates and 7 flat plates, 24 pieces. "
    f"Those are stock of parts {ids} in LRD F1-R5C4. SLN stock 67 is the other bag, unopened. "
    "Its '10 pairs / 20 pieces' is the listing, not a count. Split it into the same three parts "
    "when it is opened.</p>"))

bad = []
for ppk, spk, q in made:
    s = StockItem.objects.get(pk=spk)
    p = Part.objects.get(pk=ppk)
    print(f"part {p.pk} {p.name} | stock {s.pk} x{s.quantity:g} @ {s.location.pathstring} | home "
          f"{p.default_location.pathstring if p.default_location else '-'}")
    if s.quantity != q or s.location_id != loc.pk or p.default_location_id != loc.pk or not s.notes.exists():
        bad.append(spk)
if "split" not in Part.objects.get(pk=765).description:
    bad.append("765 desc")
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
