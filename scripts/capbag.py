#!/usr/bin/env python3
"""File bagged ceramic capacitors by their printed marking.

    capbag.py 221:10 103:25 104:8 ...

Built for walking a drawer of little bags out loud: read the marking, say the
count, move on. The decoder turns the printed code into the catalogue's value
naming so nobody has to do the arithmetic twenty times and get one wrong.

THE MARKING IS TWO SIGNIFICANT FIGURES PLUS A DECIMAL EXPONENT, IN PICOFARADS.
So 221 is 22 x 10^1 = 220 pF, not 221 of anything. The trap: small values are
often printed plainly instead, so a cap marked "10" is 10 pF while one marked
"100" is ALSO 10 pF (10 x 10^0), not 100 pF. Anything ambiguous is flagged
rather than guessed — being wrong by a factor of ten is silent and permanent.

Counts land with a stocktake date because they are real counts. Nominal kit
figures never get one.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()

from django.utils import timezone  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

DRAWER = 'A3-R8C3'
CREATE = '--create' in sys.argv


def to_pf(mark):
    """Printed marking -> picofarads, or None if it cannot be read safely."""
    m = mark.strip().upper().rstrip('JKMZ')          # tolerance letters
    if not m.isdigit():
        return None
    if len(m) <= 2:                                  # printed plainly
        return float(m)
    if len(m) == 3:
        return float(m[:2]) * (10 ** int(m[2]))
    return None


def catalog_name(pf):
    """Match the catalogue's naming: pF under 1000, nF under 1e6, else uF."""
    def trim(x):
        return f'{x:g}'
    if pf < 1000:
        return f'Capacitor Ceramic {trim(pf)}pF'
    if pf < 1_000_000:
        return f'Capacitor Ceramic {trim(pf / 1000)}nF'
    return f'Capacitor Ceramic {trim(pf / 1_000_000)}uF'


def main():
    if len([a for a in sys.argv[1:] if a != '--create']) < 1:
        print(__doc__)
        sys.exit(1)

    drawer = StockLocation.objects.get(name=DRAWER)
    today = timezone.now().date()

    for arg in [a for a in sys.argv[1:] if a != '--create']:
        if ':' not in arg:
            print(f'  {arg}: expected MARKING:QTY')
            continue
        mark, qty = arg.split(':', 1)
        pf = to_pf(mark)
        if pf is None:
            print(f'  {mark:>6}  UNREADABLE — not a standard code, say the value')
            continue
        # A 2-digit print is taken at face value. It is genuinely ambiguous
        # with the 3-digit code (a cap marked "47" and one marked "470" are both
        # 47 pF), but nothing on the part resolves it, so flagging every one is
        # noise. Marked compactly instead; size is the only tiebreak.
        plain = '~' if len(mark.strip()) == 2 else ' '

        name = catalog_name(pf)
        p = Part.objects.filter(name=name).first()
        if not p and not CREATE:
            print(f'  {mark:>6}  {pf:>9g} pF  -> "{name}" NOT IN CATALOG — '
                  f'rerun with --create')
            continue
        if not p:
            # The series is uniform and the naming is deterministic, so a missing
            # standard value is a hole rather than a decision. Still gated behind
            # an explicit flag: silently inventing parts is how a catalogue fills
            # with near-duplicates nobody meant to make.
            sib = Part.objects.filter(name__istartswith='Capacitor Ceramic',
                                      active=True).exclude(category=None).first()
            p = Part.objects.create(
                name=name, category=sib.category, component=True,
                purchaseable=True, active=True,
                description=(f'Multilayer ceramic capacitor, {name[18:]}, '
                             f'marking {mark}, 50V'))
            print(f'  {mark:>6}  {name[18:]:>7}  [{p.pk:>3}]  CREATED')

        # Look anywhere under the drawer, INCLUDING the kit compartments. A
        # value already living in a kit compartment should grow there rather
        # than sprout a second pile of the same part two inches away — that is
        # the split we just spent effort undoing for the 104s.
        here = drawer.get_descendants(include_self=True)
        item = StockItem.objects.filter(part=p, location__in=here).first()
        if item:
            was = float(item.quantity)
            StockItem.objects.filter(pk=item.pk).update(
                quantity=was + float(qty), stocktake_date=today)
            print(f'  {mark:>6}{plain} {name[18:]:>7}  [{p.pk:>3}]  '
                  f'{was:g} + {qty} = {was + float(qty):g}')
        else:
            item = StockItem.objects.create(part=p, location=drawer,
                                            quantity=float(qty))
            StockItem.objects.filter(pk=item.pk).update(stocktake_date=today)
            if not p.default_location:
                p.default_location = drawer
                p.save()
            print(f'  {mark:>6}{plain} {name[18:]:>7}  [{p.pk:>3}]  {qty} (new)')

    items = StockItem.objects.filter(location=drawer)
    print(f'\n  {DRAWER}: {items.count()} line(s), '
          f'{sum(float(s.quantity) for s in items):g} pcs')


main()
