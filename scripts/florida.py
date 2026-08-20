#!/usr/bin/env python3
"""Florida earmark and packing list.

The problem this solves: an allocation says a part is spoken for, but it does
not get the part into a box. Half the mailbox project is bound for LRD and half
stays at SLN, and the two halves sit in the same red bin looking identical.

Rather than move or split stock - which would misstate where things physically
are, and split counts that are currently correct - each stock item carries a
Florida earmark in its metadata plus a 'florida' tag for visibility in the UI.
The stock stays exactly where it is and stays usable; the earmark is a note that
survives until someone packs it.

    itq run florida.py list
    itq run florida.py add 103 RB-03 1 "Mailbox node for LRD"
    itq run florida.py drop 103 RB-03

Metadata shape, on StockItem.metadata:
    {"florida": {"qty": 1, "why": "...", "added": "YYYY-MM-DD"}}
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()

from django.utils import timezone  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

KEY = 'florida'


def _items():
    """Every stock item carrying an earmark, plus anything already in a box."""
    out = []
    for s in StockItem.objects.all().select_related('part', 'location'):
        meta = (s.metadata or {}).get(KEY)
        if meta:
            out.append((s, meta, 'earmarked'))
        elif s.location and s.location.name.startswith('FL-'):
            out.append((s, {'qty': float(s.quantity),
                            'why': 'already in the box'}, 'packed'))
    return out


def cmd_list():
    rows = _items()
    if not rows:
        print('Florida packing list is empty.')
        return
    packed = [r for r in rows if r[2] == 'packed']
    marked = [r for r in rows if r[2] == 'earmarked']

    print('=' * 74)
    print('FLORIDA PACKING LIST'.center(74))
    print('=' * 74)

    if packed:
        print('\nALREADY IN A BOX')
        for s, m, _ in packed:
            print(f'   {float(s.quantity):>4g}  [{s.part.pk:>3}] '
                  f'{s.part.name[:44]:46} {s.location.name}')

    if marked:
        print('\nEARMARKED - still on the shelf, must be collected before the trip')
        for s, m, _ in marked:
            loc = s.location.name if s.location else '-'
            of = f' of {float(s.quantity):g}' if float(m.get('qty', 0)) < \
                float(s.quantity) else ''
            print(f'   {float(m.get("qty", 0)):>4g}{of}  [{s.part.pk:>3}] '
                  f'{s.part.name[:40]:42} {loc:10} {m.get("why", "")[:30]}')

    total = sum(float(m.get('qty', 0)) for _, m, _ in rows)
    print(f'\n{len(rows)} line(s), {total:g} item(s) bound for Florida')


def cmd_add(part_pk, locname, qty, why):
    loc = StockLocation.objects.get(name=locname)
    s = StockItem.objects.filter(part_id=int(part_pk), location=loc).first()
    if not s:
        print(f'no stock of part {part_pk} in {locname}')
        sys.exit(1)
    if float(qty) > float(s.quantity):
        print(f'only {float(s.quantity):g} on hand in {locname}; refusing to '
              f'earmark {qty}')
        sys.exit(1)
    meta = s.metadata or {}
    meta[KEY] = {'qty': float(qty), 'why': why,
                 'added': str(timezone.now().date())}
    s.metadata = meta
    s.save()
    s.tags.add('florida')
    print(f'earmarked {float(qty):g} of {float(s.quantity):g} x '
          f'{s.part.name[:44]} in {locname}')
    print(f'   why: {why}')


def cmd_drop(part_pk, locname):
    loc = StockLocation.objects.get(name=locname)
    s = StockItem.objects.filter(part_id=int(part_pk), location=loc).first()
    meta = s.metadata or {}
    if KEY in meta:
        del meta[KEY]
        s.metadata = meta
        s.save()
        s.tags.remove('florida')
        print(f'earmark removed from {s.part.name[:48]} in {locname}')
    else:
        print('no earmark on that item')


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] == 'list':
        cmd_list()
    elif sys.argv[1] == 'add':
        cmd_add(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif sys.argv[1] == 'drop':
        cmd_drop(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
