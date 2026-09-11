#!/usr/bin/env python3
"""Commuting TOOLS — the ones that go to Florida and come back.

Not the same problem as `florida.py`, and deliberately not the same script.
A florida earmark is a ONE-WAY transfer: a consumable gets packed, used at
LRD, and never returns. A commuting tool is the SAME PHYSICAL OBJECT at two
addresses six months apart. Scott, 2026-09-10: *"I'm trying to figure out how
to keep track of tools that may want to go back and forth rather than buying
2 of everything"* — and, on one-way transfers, *"don't need as much
attention."*

WHY THIS EXISTS. A tool at the wrong end is worse than a tool you do not own,
because you think you have it. That is what makes someone buy a second one.
So the fact worth protecting is not "is it spoken for" but **where is it right
now**, answerable in January without walking the shop.

THE AWAY HOME IS LEARNED ON ARRIVAL, NEVER ASSIGNED IN ADVANCE.
`land` is the only thing that sets an away location, and it is run when the
tool is physically in your hand at the other end. Pre-assigning a tool to an
LRD cabinet from New Hampshire is allocation-by-plan — the same mistake that
produced the two unlocated SHT31 rows in August. As of 2026-09-10 the LRD
bench wall exists as locations and is EMPTY; Scott: *"we need to set all that
up down there still."* So early landings will be LRD/Receiving or a box, and
that is correct. The cabinet comes later, as another `land`.

    itq run scripts/trip.py where profiler        # <- the buy-time check
    itq run scripts/trip.py list
    itq run scripts/trip.py mark 797 "source meter, no second one at LRD"
    itq run scripts/trip.py pack SLN              # the list you carry
    itq run scripts/trip.py land 797 Receiving
    itq run scripts/trip.py land 797 home         # the April return

Metadata shape, on StockItem.metadata — mirrors florida.py on purpose:
    {"commutes": {"home": <loc pk>, "home_path": "...", "since": "YYYY-MM-DD",
                  "note": "...", "trips": [{"on": "...", "to": "..."}]}}

`home` is captured from where the tool sits when it is marked, and is the
RETURN ADDRESS. It is stored on the row rather than read from
Part.default_location because default_location is editable for other reasons
and this has to survive that.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()

from django.db.models import Q  # noqa: E402
from django.utils import timezone  # noqa: E402

from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

KEY = 'commutes'
BASE = 'http://192.168.50.10:8001'


def site_of(loc):
    """Top-level root of a location — 'SLN', 'LRD', or None if unlocated."""
    return loc.pathstring.split('/')[0] if loc else None


def marked():
    """Every stock row carrying a commute marker."""
    out = []
    for s in StockItem.objects.all().select_related('part', 'location'):
        m = (s.metadata or {}).get(KEY)
        if m:
            out.append((s, m))
    return sorted(out, key=lambda r: r[0].part.name.lower())


def _save_meta(s, meta):
    """.save() can report success and write nothing — verify, then fall back.

    See memory `inventree-silent-save`. The queryset .update() is the fallback
    because it bypasses the model layer entirely; safe here because metadata
    is a plain JSON field with no pathstring or tree side effects.
    """
    s.metadata = meta
    s.save()
    s.refresh_from_db()
    if (s.metadata or {}).get(KEY) != meta.get(KEY):
        StockItem.objects.filter(pk=s.pk).update(metadata=meta)
        s.refresh_from_db()
    return (s.metadata or {}).get(KEY) == meta.get(KEY)


def _resolve_item(pk):
    """Accept a StockItem pk, or a Part pk that has exactly one row."""
    s = StockItem.objects.filter(pk=int(pk)).first()
    if s:
        return s
    rows = list(StockItem.objects.filter(part_id=int(pk)))
    if len(rows) == 1:
        return rows[0]
    if not rows:
        print(f'✗ no stock item {pk}, and part {pk} has no stock rows')
    else:
        print(f'✗ part {pk} has {len(rows)} stock rows — name the row, not the part:')
        for r in rows:
            print(f'    {r.pk}  qty={float(r.quantity):g}  '
                  f'{r.location.pathstring if r.location else "NO LOCATION"}')
    sys.exit(1)


def cmd_mark(pk, note=''):
    s = _resolve_item(pk)
    if not s.location:
        print(f'✗ {s.part.name} has no location — a commuting tool needs a home '
              f'to return to. File it first.')
        sys.exit(1)
    meta = s.metadata or {}
    if KEY in meta:
        print(f'! already marked; home stays {meta[KEY].get("home_path")}')
    meta[KEY] = {
        'home': s.location.pk,
        'home_path': s.location.pathstring,
        'since': str(timezone.now().date()),
        'note': note,
        'trips': meta.get(KEY, {}).get('trips', []),
    }
    if not _save_meta(s, meta):
        print('✗ metadata did not persist')
        sys.exit(1)
    s.tags.add('commutes')
    print(f'✓ {s.part.name[:52]} commutes')
    print(f'   home: {s.location.pathstring}')
    if note:
        print(f'   why:  {note}')


def cmd_unmark(pk):
    s = _resolve_item(pk)
    meta = s.metadata or {}
    if KEY not in meta:
        print('! not marked as commuting')
        return
    del meta[KEY]
    s.metadata = meta
    s.save()
    s.refresh_from_db()
    if KEY in (s.metadata or {}):
        StockItem.objects.filter(pk=s.pk).update(metadata=meta)
    s.tags.remove('commutes')
    print(f'✓ {s.part.name[:52]} no longer marked as commuting')


def cmd_list():
    rows = marked()
    if not rows:
        print('No tools marked as commuting.')
        print('Mark one:  itq run scripts/trip.py mark <stockitem pk> "why"')
        return
    print('=' * 78)
    print('COMMUTING TOOLS'.center(78))
    print('=' * 78)
    home_n = away_n = lost_n = 0
    for s, m in rows:
        here = s.location.pathstring if s.location else None
        if here is None:
            glyph, state, lost_n = '✗', 'NO LOCATION', lost_n + 1
        elif s.location.pk == m.get('home'):
            glyph, state, home_n = '⌂', 'home', home_n + 1
        else:
            glyph, state, away_n = '→', f'AWAY at {site_of(s.location)}', away_n + 1
        print(f'\n {glyph} [{s.part.pk}] {s.part.name[:58]}')
        print(f'     {state:<22} {here or "-"}')
        if glyph != '⌂':
            print(f'     returns to             {m.get("home_path")}')
        if m.get('note'):
            print(f'     {m["note"][:66]}')
        print(f'     {BASE}/web/stock/item/{s.pk}/')
    print(f'\n{len(rows)} tool(s): {home_n} home ⌂, {away_n} away →, '
          f'{lost_n} unlocated ✗')


def cmd_pack(site='SLN'):
    """What commutes and is currently at the site you are LEAVING."""
    site = site.upper()
    rows = [(s, m) for s, m in marked() if site_of(s.location) == site]
    print('=' * 78)
    print(f'TOOLS TO PACK — leaving {site}'.center(78))
    print('=' * 78)
    if not rows:
        print(f'\nNothing marked as commuting is currently at {site}.')
        return
    for s, m in rows:
        print(f'\n  [ ] [{s.part.pk}] {s.part.name[:58]}')
        print(f'        now at {s.location.pathstring}')
        if m.get('note'):
            print(f'        {m["note"][:64]}')
    print(f'\n{len(rows)} tool(s) to collect.')
    print('\nOn arrival, record where each one actually went:')
    print('   itq run scripts/trip.py land <stockitem pk> <location name>')
    print('Do NOT pre-assign those locations from here.')


def cmd_land(pk, locname):
    """Record where a tool ACTUALLY ended up. The only thing that moves it."""
    s = _resolve_item(pk)
    meta = s.metadata or {}
    m = meta.get(KEY)
    if not m:
        print(f'✗ {s.part.name[:48]} is not marked as commuting. Mark it first '
              f'so it has a return address.')
        sys.exit(1)

    if locname.lower() == 'home':
        loc = StockLocation.objects.filter(pk=m['home']).first()
        if not loc:
            print(f'✗ home location {m["home"]} no longer exists')
            sys.exit(1)
    else:
        hits = list(StockLocation.objects.filter(
            Q(name__iexact=locname) | Q(pathstring__iexact=locname)))
        if not hits:
            hits = list(StockLocation.objects.filter(name__icontains=locname))
        if not hits:
            print(f'✗ no location matching {locname!r}')
            sys.exit(1)
        if len(hits) > 1:
            print(f'✗ {locname!r} matches {len(hits)} locations — be specific:')
            for h in hits[:12]:
                print(f'    {h.pk}  {h.pathstring}')
            sys.exit(1)
        loc = hits[0]

    was = s.location.pathstring if s.location else 'NO LOCATION'
    s.location = loc
    s.save()
    s.refresh_from_db()
    if s.location_id != loc.pk:
        StockItem.objects.filter(pk=s.pk).update(location=loc)
        s.refresh_from_db()
    if s.location_id != loc.pk:
        print('✗ move did not persist')
        sys.exit(1)

    m.setdefault('trips', []).append(
        {'on': str(timezone.now().date()), 'to': loc.pathstring})
    meta[KEY] = m
    _save_meta(s, meta)

    at_home = loc.pk == m['home']
    print(f'✓ {s.part.name[:52]}')
    print(f'   {was}')
    print(f'   -> {loc.pathstring}   {"⌂ home" if at_home else "→ away"}')
    if not at_home and site_of(loc) == site_of(
            StockLocation.objects.get(pk=m['home'])):
        print('   ! same site as its home — that is a re-file, not a trip.')


def cmd_where(*terms):
    """The buy-time check. Answers 'you already own one, it is at X'."""
    q = ' '.join(terms).strip()
    if not q:
        print('usage: trip.py where <search terms>')
        sys.exit(1)

    parts = Part.objects.filter(
        Q(name__icontains=q) | Q(description__icontains=q)
        | Q(keywords__icontains=q) | Q(IPN__icontains=q)
    ).distinct()

    print(f'"{q}" — {parts.count()} part(s)\n')
    if not parts:
        print('✗ Nothing matches. NOT proof the shop has none — this searched')
        print('  name, description, keywords and IPN in InvenTree only, and a')
        print('  tool that was never catalogued is invisible here. See')
        print('  docs/TRAPS.md on searching a purchase by its product name.')
        return

    for p in parts.order_by('name'):
        rows = list(StockItem.objects.filter(part=p).select_related('location'))
        flag = '' if p.active else '   [INACTIVE — merged away]'
        print(f'  [{p.pk}] {p.name[:60]}{flag}')
        if not rows:
            print('        ✗ no stock rows — catalogued but not filed, or not owned')
        for s in rows:
            c = (s.metadata or {}).get(KEY)
            site = site_of(s.location) or 'NOWHERE'
            mark = ''
            if c:
                mark = ('  ⌂ commutes, at home' if s.location
                        and s.location.pk == c['home']
                        else f'  → COMMUTES, away from {c["home_path"]}')
            print(f'        {float(s.quantity):g} at {site}: '
                  f'{s.location.pathstring if s.location else "-"}{mark}')
        print(f'        {BASE}/web/part/{p.pk}/')
        print()


if __name__ == '__main__':
    a = sys.argv[1:]
    cmd = a[0] if a else 'list'
    if cmd == 'list':
        cmd_list()
    elif cmd == 'mark':
        cmd_mark(a[1], a[2] if len(a) > 2 else '')
    elif cmd == 'unmark':
        cmd_unmark(a[1])
    elif cmd == 'pack':
        cmd_pack(a[1] if len(a) > 1 else 'SLN')
    elif cmd == 'land':
        cmd_land(a[1], a[2])
    elif cmd == 'where':
        cmd_where(*a[1:])
    else:
        print(__doc__)
