"""Record the loose swap-meet headers as two assortment units (2026-11-02).

Scott split the loose lot by gender: male headers join the bagged 2x5/2x8 in
F1-R5C5, and female sockets get their own drawer, F1-R5C7, because "there's
enough of it here". Part 1471 was made minutes earlier as one mixed lot and
nobody had seen it yet. It is renamed to the male lot rather than deleted, and
a female twin is created. Each is ONE unit, the whole lot, not itemised (Scott).
$0, HOT club swap meet.

    itq run scripts/swap_meet_header_lots_1102.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from djmoney.money import Money  # noqa: E402
from common.models import Note  # noqa: E402
from InvenTree.status_codes import StockHistoryCode  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

commit = "--commit" in sys.argv
SRC = "HOT club swap meet, $0 (Scott, 2026-11-02)."
male_loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R5C5")
fem_loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R5C7")
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
male = Part.objects.get(pk=1471)
assert not StockItem.objects.filter(part=male).exists()
held = StockItem.objects.filter(location=fem_loc)
assert not held.exists(), f"F1-R5C7 holds {list(held.values_list('pk', 'part__name'))}"
FEM = "Pin Socket Assortment 2.54mm, female, mixed sizes (swap meet lot)"
print("rename 1471 ->", "Pin Header Assortment 2.54mm, male, mixed sizes (swap meet lot)", "@ F1-R5C5")
print("new part    ->", FEM, "@ F1-R5C7")
if not commit:
    raise SystemExit("DRY RUN - add --commit")

male.name = "Pin Header Assortment 2.54mm, male, mixed sizes (swap meet lot)"
male.description = ("Loose male pin headers, assorted sizes. ONE unit = the whole lot, not "
                    "itemised on purpose. Female sockets from the same lot: see the female twin")
male.default_location = male_loc
male.save()
fem = Part.objects.filter(name=FEM).first()
if fem is None:
    fem = Part(name=FEM, category=male.category, component=True, purchaseable=False,
               default_location=fem_loc,
               description=("Loose female pin sockets, assorted sizes. ONE unit = the whole lot, "
                            "not itemised on purpose. Male headers from the same lot: part 1471"))
    fem.save()
    Note.objects.create(content_object=fem, title="Source", primary=True, content=(
        f"{SRC} Split from the male headers into its own drawer, F1-R5C7, because there "
        "is enough of it (Scott). An assortment is one unit, not a multipack."))
Note.objects.create(content_object=male, title="Split", primary=False, content=(
    f"2026-11-02: female sockets split out to part {fem.pk} (F1-R5C7). This part is now the male lot only."))

made = []
for p, loc in ((male, male_loc), (fem, fem_loc)):
    s = StockItem(part=p, location=loc, quantity=1, purchase_price=Money(0, "USD"))
    s.save()
    s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 1.0},
                         notes=f"Whole loose lot into {loc.name}. {SRC}")
    made.append((p.pk, s.pk, loc))
bad = []
for ppk, spk, loc in made:
    p, s = Part.objects.get(pk=ppk), StockItem.objects.get(pk=spk)
    print(f"part {p.pk} {p.name} | stock {s.pk} x{s.quantity:g} @ {s.location.pathstring}")
    if s.quantity != 1 or s.location_id != loc.pk or p.default_location_id != loc.pk:
        bad.append(spk)
if "male, mixed" not in Part.objects.get(pk=1471).name:
    bad.append("1471 name")
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
