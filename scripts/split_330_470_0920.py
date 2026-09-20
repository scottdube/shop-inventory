"""Split the last three resistors of the G1000 PFD bag to Florida Staging.

2 x 330R (row 138) and 1 x 470R (row 140), both from the EAONE 30-value kit.
These are the BACKUP for R9/R10/R15 - the primary is the ALLECIN 1/2W kit
confirmed at LRD, which holds 10 of each value. Scott is carrying these
because February proves where that box arrived, not that it is on a shelf
today.

TWO THINGS TO BE HONEST ABOUT IN THE RECORD:

1. The source quantities are [ESTIMATE], not counts - 850 pcs / 30 values.
   Splitting off an estimate leaves an estimate. The remainders below are
   arithmetic on a guess and must not read as measurements.

2. ZERO MARGIN. 2 and 1 are exactly what the board needs. Drop one on the
   floor at LRD and the ALLECIN kit is the only recovery.

Source florida tags are cleared: the earmark is now embodied in the new rows
and leaving it in place double-counts. Same trap as row 125 this morning.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from stock.models import StockItem, StockLocation
from django.contrib.auth import get_user_model
from datetime import date

COMMIT = '--commit' in sys.argv
user = get_user_model().objects.filter(is_superuser=True).first()
BAG = StockLocation.objects.get(pk=503)
BATCH = "G1000 PFD build #3"

JOBS = [
    (138, 2, 'R9 and R10, the 2-LED groups', 'spec is 300R; 330R is the nearest E24 value, ~10% dimmer'),
    (140, 1, 'R15, the single-LED group', 'spec is 450R; 470R is the nearest E24 value, ~4% dimmer'),
]

for pk, take, where, sub in JOBS:
    src = StockItem.objects.get(pk=pk)
    print(f"source row {pk} [{src.part.pk}] {src.part.name}")
    print(f"  qty={src.quantity} loc={src.location.name}")
    print(f"  tags={[t.name for t in src.tags.all()]} meta={src.metadata}")
    print(f"  taking {take} -> Florida Staging, leaving {src.quantity - take}")

if not COMMIT:
    print("\nDRY RUN - rerun with --commit"); sys.exit(0)

for pk, take, where, sub in JOBS:
    src = StockItem.objects.get(pk=pk)
    new = src.splitStock(take, location=BAG, user=user)
    new.batch = BATCH
    new.metadata = {'florida': {
        'qty': float(take),
        'why': f'G1000 build #3 (PFD) at LRD - BO-0017 - {where}',
        'added': str(date.today())}}
    new.notes = f"""Split from row {pk} (EAONE kit, L2-D4) on 2026-09-20 for the Florida bag.

FOR {where.upper()}. {sub[0].upper()}{sub[1:]}.

THIS IS THE BACKUP, NOT THE PRIMARY. The ALLECIN 25-value 1/2W kit (part #1)
is confirmed at LRD by Amazon order 113-4288189-7490647 and holds 10 of this
value in 1/2W, which is the rating this board's footprint prefers. Fit from
that kit first; these travel because a February shipping address proves where
the box arrived, not that it is on the shelf today.

ZERO MARGIN. This is exactly the board count. There is no spare.

QUANTITY INHERITS AN ESTIMATE. The source row was never counted - it was the
kit label's 850 pcs / 30 values. These {take} were physically picked, so the
count of THIS row is real; the source's remainder is not."""
    new.save()
    new.tags.add('florida')

    src = StockItem.objects.get(pk=pk)
    src.metadata = {}
    src.notes = (src.notes or '') + f"""

2026-09-20: {take} split out to Florida Staging (row {new.pk}) for the G1000
PFD build. The in-place florida earmark was dropped here so it cannot
double-count against that row.
REMAINDER IS ARITHMETIC ON AN ESTIMATE, NOT A COUNT: the {src.quantity + take}
was itself 850/30, never tallied. Correct the whole row on a physical count."""
    src.save()
    src.tags.remove('florida')

    s = StockItem.objects.get(pk=pk); n = StockItem.objects.get(pk=new.pk)
    print(f"\nAFTER {pk}: qty={s.quantity} loc={s.location.name} tags={[t.name for t in s.tags.all()]} meta={s.metadata}")
    print(f"AFTER {n.pk}: qty={n.quantity} loc={n.location.name} batch={n.batch!r} "
          f"tags={[t.name for t in n.tags.all()]} florida={(n.metadata or {}).get('florida',{}).get('qty')}")
    ok = (n.location_id == BAG.pk and n.batch == BATCH and 'florida' in [t.name for t in n.tags.all()]
          and 'florida' not in [t.name for t in s.tags.all()] and not (s.metadata or {}))
    print("VERIFIED" if ok else "*** VERIFY FAILED ***")
