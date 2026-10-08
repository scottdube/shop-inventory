#!/usr/bin/env python3
"""Pack 4 of each RF pigtail (stock 603, 604 in A3-R6C6) into FL-01.

Scott, 2026-10-08, after bagging and labelling them: "shouldn't this now say
5 at sln 4 lrd?" Yes to the split, no to LRD: the 4 go to FL-01, the carry
box at SLN, and get an LRD location on ARRIVAL (same rule as trip.py land).

Split, not move: 4 of 8 and 4 of 9 are leaving, the rest stay in the drawer.
The earmark on the drawer row is DROPPED, because the FL-01 row now reports
as 'packed' and the drawer row no longer has anything bound for Florida.
splitStock copies metadata to the new row, so the key is stripped there too
(florida.py reads metadata before the FL- location test; carrying both
would report a packed item as merely earmarked - see pack_rpi3b_florida.py).

default_location is left alone: the drawer is still home for the remainder.

    itq run scripts/pack_pigtails_florida_1008.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
FL = StockLocation.objects.get(pk=504)
assert FL.name == 'FL-01', FL.pathstring
user = get_user_model().objects.filter(is_superuser=True).order_by('pk').first()
PLAN = [(603, 4), (604, 4)]

def strip(s):
    meta = dict(s.metadata or {})
    meta.pop('florida', None)
    StockItem.objects.filter(pk=s.pk).update(metadata=meta)
    s.refresh_from_db()
    s.tags.remove('florida')
    return 'florida' not in (s.metadata or {})

for pk, n in PLAN:
    s = StockItem.objects.get(pk=pk)
    print(f"[{s.pk}] {s.quantity:g} x {s.part.name[:50]} @ {s.location.pathstring}")
    print(f"      earmark: {(s.metadata or {}).get('florida')}")
    print(f"      plan: split {n} -> {FL.pathstring}, leave {s.quantity - n:g}")
    if not COMMIT:
        continue
    new = s.splitStock(n, FL, user, notes='Packed for Florida 2026-10-08 (Scott: 4 of each)')
    s.refresh_from_db(); new.refresh_from_db()
    ok = strip(s) and strip(new)
    print(f"      -> [{new.pk}] {new.quantity:g} @ {new.location.pathstring}; "
          f"[{s.pk}] now {s.quantity:g} @ {s.location.name}; earmarks cleared: {ok}")

if not COMMIT:
    print("\nDRY RUN - nothing written. Re-run with --commit.")
