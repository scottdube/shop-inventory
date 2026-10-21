#!/usr/bin/env python3
"""READ-ONLY prep for the LRD drawer walk (photos of 2026-10-21).

For each drawer photo, search InvenTree by REQUIREMENT terms (what the thing
is), not by a chosen part number, and print every part that matches with its
stock rows, site and commute mark — so the catalogue session knows what
already exists before it creates anything. Writes nothing.

Also prints the 15 drawer locations' current descriptions (a drawer with 0
rows is "unrecorded", and the description is where the walk is recorded), and
whether StockLocation can carry attachments on this 1.6 install.

    itq run scripts/lrd_drawer_search_1021.py
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()

from django.db.models import Q  # noqa: E402

from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

BASE = 'http://192.168.50.10:8001'
CAP = 10  # matches shown per term; the count is always printed

# photo -> requirement terms read off the photo (identity only)
PHOTOS = {
    '02 (Cab4-D1?)': ['Knipex', 'Klein', 'cutter', 'plier', 'screwdriver',
                      'tape measure', 'caliper', 'scissor', '9V', 'level'],
    '03 (Cab4-D2?)': ['adjustable wrench', 'crescent', 'hex key', 'allen',
                      'Kobalt', 'Brady', 'M21', 'Wiha', 'impact bit', 'AA batt'],
    '04 (Cab4-D3?)': ['tool bag', 'Ryobi', 'hammer', 'torpedo', 'clamp meter',
                      'NCVT', 'tone', 'stud finder', 'Zircon', 'outlet tester'],
    '05 (Cab4-D4?)': ['xTool', 'logic analy', 'Lonely Binary', 'Pi case',
                      'Raspberry', 'NooElec', 'SDR'],
    '06 (Cab4-D5?)': ['Quinn'],
    '07 (Cab3-D1?)': ['micro screw', 'PA screw', 'Zmbroll', 'M2 ', 'wire nut',
                      'RJ45', 'keystone', 'Tempest', 'cable clip'],
    '08 (Cab3-D2?)': ['magnet', 'Grip-Rite', 'anchor', 'drywall', 'wood screw'],
    '09 (Cab3-D3?)': ['hacksaw', 'hole saw', 'multi-tool', 'oscillating',
                      'insulated screwdriver', 'zip tie', 'cable tie'],
    '10 (Cab3-D4?)': ['sanding drum', 'Sunxeke', 'P-touch', 'Brother',
                      'Einstar', 'Vega'],
    '11 (Cab3-D5?)': [],  # empty drawer
    '12 (Cab2-D1?)': ['crimper', 'crimp', 'LAN Scout', 'punch', 'stripper',
                      'USB cable', 'Seeed'],
    '13 (Cab2-D2?)': ['Tokego', 'soldering station', 'soldering iron',
                      'heat shrink', 'Ginsco', 'tracer', 'fish tape',
                      'heat gun', 'hot air', 'wall plate', 'VCELINK'],
    '14 (Cab2-D3?)': ['socket set', 'resistor kit', 'capacitor kit', 'Warrior',
                      'drill bit', 'drill set', 'masonry', 'perf', 'proto'],
    '15 (Cab2-D4?)': ['ferrule', 'Someline', 'breadboard', 'Makeronics',
                      'ESP32', 'relay module', 'jumper', 'alligator'],
    '16 (Cab2-D5?)': ['LED strip', 'MDF', 'acrylic sign'],
}


def site_of(loc):
    if not loc:
        return None
    return loc.pathstring.split('/')[0]


def search(term):
    return Part.objects.filter(
        Q(name__icontains=term) | Q(description__icontains=term)
        | Q(keywords__icontains=term) | Q(IPN__icontains=term)
    ).distinct().order_by('name')


def show_part(p):
    rows = list(StockItem.objects.filter(part=p).select_related('location'))
    flag = '' if p.active else '  [INACTIVE]'
    print(f'      [{p.pk}] {p.name[:70]}{flag}')
    if not rows:
        print('            no stock rows')
    for s in rows:
        c = (s.metadata or {}).get('commutes')
        site = site_of(s.location) or 'NOWHERE'
        mark = ''
        if c:
            mark = ('  commutes, at home' if s.location
                    and s.location.pk == c['home']
                    else f'  COMMUTES, away from {c["home_path"]}')
        print(f'            {float(s.quantity):g} at {site}: '
              f'{s.location.pathstring if s.location else "-"}{mark}')


print('=== drawer locations (description is the record; 0 rows = unrecorded) ===')
for loc in StockLocation.objects.filter(pk__in=range(627, 642)).order_by('pk'):
    n = StockItem.objects.filter(location=loc).count()
    print(f'  [{loc.pk}] {loc.pathstring}  rows={n}  desc={loc.description!r}')
for pk in (524, 530, 531, 532):
    loc = StockLocation.objects.get(pk=pk)
    print(f'  [{loc.pk}] {loc.pathstring}  desc={loc.description!r}')

print('\n=== can StockLocation carry attachments on 1.6? ===')
try:
    from common.models import Attachment
    from django.contrib.contenttypes.models import ContentType
    ct = ContentType.objects.get_for_model(StockLocation)
    allowed = getattr(StockLocation, 'attachments', None) is not None
    print(f'  StockLocation.attachments attr: {allowed}; '
          f'existing Attachment rows for stock.stocklocation: '
          f'{Attachment.objects.filter(model_type=ct.model).count()}')
    from InvenTree.models import InvenTreeAttachmentMixin
    print(f'  InvenTreeAttachmentMixin in MRO: '
          f'{InvenTreeAttachmentMixin in StockLocation.__mro__}')
except Exception as e:  # noqa: BLE001
    print(f'  check failed: {type(e).__name__}: {e}')

print('\n=== requirement search, per photo ===')
seen_total = set()
for photo, terms in PHOTOS.items():
    print(f'\n--- photo {photo} ---')
    if not terms:
        print('  (empty drawer, nothing to search)')
        continue
    for t in terms:
        qs = search(t)
        n = qs.count()
        if n == 0:
            print(f'  "{t}": 0')
            continue
        print(f'  "{t}": {n}' + ('  (capped)' if n > CAP else ''))
        for p in qs[:CAP]:
            show_part(p)
            seen_total.add(p.pk)

print(f'\n{len(seen_total)} distinct parts shown. A 0 above is a lead, not a '
      f'finding: only name/description/keywords/IPN were searched.')
