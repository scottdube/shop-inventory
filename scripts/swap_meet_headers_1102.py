"""Enter the two bagged HOT swap-meet male pin headers at LRD into F1-R5C5 (2026-11-02).

Scott brought back two bags: 2x5 male (10-pin) and 2x8 male (16-pin), about 20
each. Those are his estimates, so the rows carry [ESTIMATE]. Price is $0 (swap meet).
The existing 2x5/2x8 parts (1245, 1243) are FEMALE sockets from the Glarks kit,
so new parts were made rather than adding rows to those.

The rest of the swap-meet lot, loose male and female headers and sockets of
assorted sizes, is deliberately NOT itemised (Scott: "just miscellaneous header
pins"). If it gets recorded, it goes in as one assortment unit, not as pieces.

    itq run scripts/swap_meet_headers_1102.py [--commit]
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
loc = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R5C5")
cat = Part.objects.get(pk=1245).category  # same category as the female 2x5 socket
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
SRC = "HOT club swap meet, $0 (Scott, 2026-11-02)."
NEW = [
    ("Pin Header 2.54mm Double Row 2x5 Male (10-pin)", "Male pin header, 2 rows x 5, 0.1 in pitch", 20),
    ("Pin Header 2.54mm Double Row 2x8 Male (16-pin)", "Male pin header, 2 rows x 8, 0.1 in pitch", 20),
]
held = StockItem.objects.filter(location=loc)
assert not held.exists(), f"F1-R5C5 holds {list(held.values_list('pk', 'part__name'))}"
for name, _, q in NEW:
    dup = Part.objects.filter(name__iexact=name)
    print(f"~{q} x {name}" + (f"  (exists: {dup.first().pk})" if dup.exists() else ""))
print("category:", cat.pathstring)
if not commit:
    raise SystemExit("DRY RUN - add --commit")
made = []
for name, desc, q in NEW:
    p = Part.objects.filter(name__iexact=name).first()  # rerun-safe
    if p is None:
        p = Part(name=name, description=desc, category=cat, component=True,
                 purchaseable=True, default_location=loc)
        p.save()
    s = StockItem(part=p, location=loc, quantity=q, purchase_price=Money(0, "USD"))
    s.save()
    Note.objects.create(content_object=s, title="Count", primary=True,
                        content=f"[ESTIMATE] ~{q}, Scott's estimate, not counted. {SRC}")
    s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": float(q)},
                         notes=f"Into F1-R5C5. {SRC}")
    made.append((p.pk, s.pk, q))
bad = []
for ppk, spk, q in made:
    s = StockItem.objects.get(pk=spk)
    p = Part.objects.get(pk=ppk)
    print(f"part {p.pk} {p.name} | stock {s.pk} x{s.quantity:g} @ {s.location.pathstring} | {s.purchase_price}")
    if s.quantity != q or s.location_id != loc.pk or p.default_location_id != loc.pk or not s.notes.exists():
        bad.append(spk)
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
