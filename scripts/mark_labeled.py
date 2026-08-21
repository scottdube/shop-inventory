#!/usr/bin/env python3
"""Record which locations already carry a physical label.

With 474 locations, "is this drawer labelled?" otherwise gets answered by
printing a duplicate and walking over to find out. Stored as metadata.labeled
alongside metadata.size, so a batch print can skip what is already done.

Usage:
    itq run mark_labeled.py NAME [NAME ...]     mark these
    itq run mark_labeled.py --cabinet A3        mark every child of A3
    itq run mark_labeled.py --rows A3 4 8       mark A3 rows 4..8 only
    itq run mark_labeled.py --report            show coverage, change nothing

Only mark what someone has actually SEEN a label on. A location wrongly flagged
as labelled is worse than one not flagged at all: the unflagged drawer gets a
spare label printed, the wrongly-flagged one stays bare forever because nothing
will ever offer to print it again.

"Labelled" means a PRINTED label carrying the QR code. Several cabinets have
handwritten paper labels ("1/4-28 NUT", "TOGGLE SWITCHES", "ARDUINOS") from
before this system existed. Those drawers are labelled in the everyday sense
and must still be flagged FALSE: they carry no QR, nothing links them to
InvenTree, and they are exactly the drawers that still need doing.
"""
import os
import re
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()

from stock.models import StockLocation  # noqa: E402


def mark(names, via='Avery sheet'):
    hit = 0
    for n in names:
        loc = StockLocation.objects.filter(name=n).first()
        if not loc:
            print(f'  ! no location named {n}')
            continue
        md = dict(loc.metadata or {})
        if md.get('labeled'):
            continue
        md['labeled'] = True
        md['labeled_via'] = via
        loc.metadata = md
        loc.save()
        loc.refresh_from_db()
        if (loc.metadata or {}).get('labeled') is not True:
            # metadata writes have silently no-opped on this install before
            StockLocation.objects.filter(pk=loc.pk).update(metadata=md)
            loc.refresh_from_db()
        if (loc.metadata or {}).get('labeled') is True:
            hit += 1
        else:
            print(f'  ! {n} did not stick — CHECK IT')
    return hit


def report():
    by_cab = {}
    for loc in StockLocation.objects.all():
        parent = loc.parent.name if loc.parent else '(root)'
        d, t = by_cab.get(parent, (0, 0))
        by_cab[parent] = (d + (1 if (loc.metadata or {}).get('labeled') else 0),
                          t + 1)
    print(f'{"parent":26} {"labelled":>9} {"total":>7}')
    for k in sorted(by_cab):
        d, t = by_cab[k]
        if t > 1:
            flag = '  <-- all done' if d == t else ''
            print(f'  {k:24} {d:>9} {t:>7}{flag}')
    tot = StockLocation.objects.count()
    done = sum(1 for l in StockLocation.objects.all()
               if (l.metadata or {}).get('labeled'))
    print(f'\n  {done} of {tot} locations recorded as labelled')


args = sys.argv[1:]
if not args or args[0] == '--report':
    report()
elif args[0] == '--cabinet':
    cab = StockLocation.objects.get(name=args[1])
    kids = [k.name for k in cab.get_children()]
    print(f'  {args[1]}: {mark(kids)} newly marked of {len(kids)}')
    report()
elif args[0] == '--rows':
    cab, lo, hi = args[1], int(args[2]), int(args[3])
    kids = []
    for k in StockLocation.objects.get(name=cab).get_children():
        m = re.match(rf'^{re.escape(cab)}-R(\d+)C\d+$', k.name)
        if m and lo <= int(m.group(1)) <= hi:
            kids.append(k.name)
    print(f'  {cab} rows {lo}-{hi}: {mark(kids)} newly marked of {len(kids)}')
    report()
else:
    print(f'  {mark(args)} newly marked')
    report()
