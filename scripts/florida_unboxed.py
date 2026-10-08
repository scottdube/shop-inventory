#!/usr/bin/env python3
"""Florida earmarks that are NOT yet in an FL- box, grouped by purpose.
Companion to florida.py list: that prints everything bound for Florida; this
prints only what still has to be physically packed, with stock pk and the
take/on-hand split, so the pack step is one line per row:
    itq run scripts/florida_pack.py <stock_pk> <qty> [<stock_pk> <qty> ...] --commit
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from stock.models import StockItem, StockLocation
from collections import defaultdict
packed, marked = [], []
for s in StockItem.objects.all().select_related('part','location'):
    m = (s.metadata or {}).get('florida')
    loc = s.location.pathstring if s.location else '-'
    if m:
        marked.append((m['why'], s, m))
    elif s.location and s.location.name.startswith('FL-'):
        packed.append(s)
print('PACKED (in an FL- box):')
for s in packed:
    print(f'  stock {s.pk:5}  {s.quantity:>6g}  {s.part.name[:58]}')
groups = defaultdict(list)
for why, s, m in marked:
    key = why.split(' - ')[0].strip() if ' - ' in why else why.split('(')[0].strip()
    groups[key].append((s, m))
print(f'\nEARMARKED, NOT BOXED: {len(marked)} rows')
for key in sorted(groups):
    print(f'\n## {key}')
    for s, m in sorted(groups[key], key=lambda r: r[0].location.pathstring if r[0].location else ''):
        loc = s.location.pathstring.replace('SLN/','') if s.location else '-'
        q = m['qty']; oh = float(s.quantity)
        print(f'  stock {s.pk:5}  take {q:>4g} of {oh:<5g} @ {loc:38}  {s.part.name[:50]}')
print('\nFL locations:')
for l in StockLocation.objects.filter(name__startswith='FL-'):
    print(f'  [{l.pk}] {l.pathstring}: {l.description}')
