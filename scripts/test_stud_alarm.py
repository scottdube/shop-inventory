import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from django.db import transaction
from stock.models import StockItem

def bare_holders():
    """Same shortfall logic as stud_check, run standalone."""
    out = []
    for hpk in (10, 12, 13):
        h = StockItem.objects.get(pk=hpk)
        fitted = sum(float(x.quantity) for x in StockItem.objects.filter(belongs_to=h)
                     if 'Pull Stud' in x.part.name and 'TSC' in x.part.name)
        short = float(h.quantity) - fitted
        out.append((h.part.name[:40], float(h.quantity), fitted, short))
    return out

print('BASELINE (real data):')
for n, q, f, s in bare_holders():
    print(f'  {"OK " if s <= 0 else "!! "} {n:<40} qty {q:g} fitted {f:g} short {s:g}')

print('\nFAULT INJECTED — detaching the 3/8" stud, inside a rolled-back transaction:')
try:
    with transaction.atomic():
        si = StockItem.objects.get(pk=758)          # the 3/8" stud
        si.belongs_to = None
        si.save()
        fired = False
        for n, q, f, s in bare_holders():
            flag = "OK " if s <= 0 else "!! "
            if s > 0:
                fired = True
            print(f'  {flag} {n:<40} qty {q:g} fitted {f:g} short {s:g}')
        assert fired, 'ALARM DID NOT FIRE — the check is decorative'
        print('\n  alarm fired correctly')
        raise RuntimeError('rollback')
except RuntimeError as e:
    if str(e) != 'rollback':
        raise

print('\nAFTER ROLLBACK (must match baseline):')
for n, q, f, s in bare_holders():
    print(f'  {"OK " if s <= 0 else "!! "} {n:<40} qty {q:g} fitted {f:g} short {s:g}')
assert all(s <= 0 for _, _, _, s in bare_holders()), 'ROLLBACK FAILED — data left dirty'
print('\nPASS — alarm fires on a bare holder, and the rollback restored the data')
