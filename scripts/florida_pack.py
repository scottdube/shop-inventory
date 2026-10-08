#!/usr/bin/env python3
"""Move earmarked stock into FL-01 once it is PHYSICALLY in the box.

Generalises pack_pigtails_florida_1008.py. Takes (stock_pk, qty) pairs:

    itq run scripts/florida_pack.py 741 1 859 50 647 5 [--commit]

Rules, all learned the hard way (see pack_rpi3b_florida.py, florida.py):
  - qty == on hand  -> the whole row MOVES to FL-01 (no split, same pk).
  - qty <  on hand  -> splitStock: a new row in FL-01, the rest stays home.
  - the 'florida' earmark key and tag are dropped on every touched row, so
    florida.py reports the FL-01 row as 'packed' and the home row as nothing.
  - default_location is NOT touched: the home drawer is still home for the
    remainder, and for a whole-row move the part's home is where a spare
    goes back to, never the box.
  - nothing is filed at LRD: the away location is recorded on arrival.
Refuses a qty above on hand, and a qty that differs from the earmark is
allowed but printed loudly so a typo cannot hide.
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from django.utils import timezone  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

args = [a for a in sys.argv[1:] if a != '--commit']
COMMIT = '--commit' in sys.argv
if len(args) < 2 or len(args) % 2:
    print(__doc__); sys.exit(1)
PLAN = [(int(args[i]), float(args[i + 1])) for i in range(0, len(args), 2)]
FL = StockLocation.objects.get(pk=504)
assert FL.name == 'FL-01', FL.pathstring
user = get_user_model().objects.filter(is_superuser=True).order_by('pk').first()
today = str(timezone.now().date())

def strip(s):
    meta = dict(s.metadata or {})
    meta.pop('florida', None)
    StockItem.objects.filter(pk=s.pk).update(metadata=meta)
    s.refresh_from_db()
    s.tags.remove('florida')
    return 'florida' not in (s.metadata or {})

bad = False
rows = []
for pk, n in PLAN:
    s = StockItem.objects.filter(pk=pk).select_related('part', 'location').first()
    if not s:
        print(f'✗ no stock item {pk}'); bad = True; continue
    oh = float(s.quantity)
    em = ((s.metadata or {}).get('florida') or {}).get('qty')
    loc = s.location.pathstring if s.location else '-'
    print(f'[{s.pk}] {oh:g} x {s.part.name[:52]} @ {loc}')
    if s.location and s.location.name.startswith('FL-'):
        print('      ✗ already in an FL- box'); bad = True; continue
    if n > oh:
        print(f'      ✗ asked {n:g}, only {oh:g} on hand'); bad = True; continue
    if em is None:
        print('      ! no florida earmark on this row — packing it anyway')
    elif em != n:
        print(f'      ! earmark says {em:g}, packing {n:g}')
    print(f'      plan: {"MOVE whole row" if n == oh else f"split {n:g}, leave {oh - n:g}"} -> {FL.pathstring}')
    rows.append((s, n))
if bad:
    print('\nREFUSED - fix the list above.'); sys.exit(1)
if not COMMIT:
    print('\nDRY RUN - nothing written. Re-run with --commit.'); sys.exit(0)

for s, n in rows:
    oh = float(s.quantity)
    note = f'Packed for Florida {today}'
    if n == oh:
        StockItem.objects.filter(pk=s.pk).update(location=FL)
        s.refresh_from_db()
        ok = strip(s)
        print(f'[{s.pk}] moved -> {s.location.pathstring}; earmark cleared: {ok}')
    else:
        new = s.splitStock(n, FL, user, notes=note)
        s.refresh_from_db(); new.refresh_from_db()
        ok = strip(s) and strip(new)
        print(f'[{s.pk}] now {s.quantity:g} @ {s.location.name}; new [{new.pk}] '
              f'{new.quantity:g} @ {new.location.pathstring}; earmarks cleared: {ok}')
