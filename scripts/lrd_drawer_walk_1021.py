#!/usr/bin/env python3
"""LRD drawer walk, phase A: record what each drawer HOLDS, on the drawer.

Photos of 2026-10-21, mapping confirmed by Scott the same day:
02-06 = Cab4-D1..D5, 07-11 = Cab3-D1..D5, 12-16 = Cab2-D1..D5, 01 = overview.

For each drawer location this writes the contents (identity only, read off
the photo) into the location DESCRIPTION after the size sentence, and
attaches the photo as a common.Attachment (model_type='stocklocation' -- the
same mechanism photo_push.py used for the SLN MB drawers on 2026-10-10).
Photo 11 is the one verified-empty drawer and is marked exactly that way.

No stock rows are created here: counts come from Scott, per drawer, in phase
B. "0 stock rows" on these locations therefore means UNRECORDED (see
docs/TRAPS.md, "Zero stock items does NOT mean the drawer is empty") and the
description says so.

    itq push /tmp/lrd-drawers-1021.tar lrd-drawers-1021.tar
    itq run scripts/lrd_drawer_walk_1021.py            # dry run
    itq run scripts/lrd_drawer_walk_1021.py --commit   # write + verify by re-read
"""
import os
import sys
import tarfile

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()

from common.models import Attachment              # noqa: E402
from django.contrib.auth import get_user_model    # noqa: E402
from django.core.files.base import ContentFile    # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = '--commit' in sys.argv
TAR = os.path.expanduser('~/lrd-drawers-1021.tar')
PHOTO_DIR = os.path.expanduser('~/lrd-drawers-1021')
WALK = 'Walked 2026-10-21 (photo attached)'
UNRECORDED = ('Not itemised yet: 0 stock rows here means UNRECORDED, not empty; '
              'counts come from Scott.')

# pk -> (photo file, contents as read off the photo; identity only)
DRAWERS = {
    637: ('02-3a08ac1f.jpg', 'hand tools: Knipex and Klein cutters/pliers, '
          'screwdrivers (Denali, others), Craftsman 25 ft tape, Vevor digital '
          'caliper (red case), scissors, 9 V battery, small level, utility '
          'knife, Sharpie, bit set, yellow legal pad'),
    638: ('03-064c7299.jpg', 'adjustable wrenches, 2x Kobalt hex-key sets, '
          'Brady M21 label cartridges, Wiha 26390 precision hex driver set, '
          'Vevor impact bit set, Duracell AA batteries, work glove, wire'),
    639: ('04-53e980a8.jpg', 'Klein tool bag, Ryobi screwdriver, hammers, '
          'torpedo levels, Klein clamp meter, NCVT, VDV tone probe, Zircon '
          'HD70 stud finder, charger, outlet tester'),
    640: ('05-f7cf8c5e.jpg', 'xTool red foam trays, Lonely Binary logic '
          'analyzer kit (part 238, commutes), Raspberry Pi cases, NooElec '
          'NESDR SDR (part 261), bagged electronics'),
    641: ('06-94835d1a.jpg', 'one Quinn hard case (contents not photographed)'),
    632: ('07-b375b3c8.jpg', 'orange grid insert + blue bins: 625-pc PA '
          'micro-screw set, Zmbroll 660-pc M2 kit, wire nuts, RJ45 plugs, '
          'keystone jacks, cable clips, Tempest mount parts'),
    633: ('08-edd3b96c.jpg', 'red grid insert, green/black bins of sorted '
          'hardware (screws, anchors, lag/wood screws, washers, nuts), 10-pc '
          'magnets 2-Q279S, Grip-Rite screw pack, a Home Depot order box'),
    634: ('09-427c69ad.jpg', 'Stanley hacksaw, hole saws, Milwaukee multi-tool '
          'blades, Milwaukee insulated screwdrivers, zip ties'),
    635: ('10-bb56d990.jpg', 'Sunxeke sanding drums, Brother P-touch label '
          'maker, Einstar Vega 3D scanner case (part 1379, commutes)'),
    636: ('11-839bdf56.jpg', None),  # VERIFIED EMPTY
    627: ('12-f24e5fbe.jpg', 'network tools: RJ45 crimper, Klein LAN Scout '
          'Jr 2, punch-down tool, wire strippers, needle-nose pliers, USB '
          'cables, Seeed box, GarageCabinets paperwork'),
    628: ('13-fe9f9b0c.jpg', 'Tokego 980E soldering station (boxed), Ginsco '
          'heat-shrink kit (part 450), Klein tone tracer, fish tape, hot-air '
          'gun, VCELINK wall plates, Tempest adapter, syringes, misc cables'),
    629: ('14-6a156042.jpg', 'socket set, resistor and capacitor kits, '
          'Warrior 29-pc drill set, masonry bits, perf boards, DigiKey bags'),
    630: ('15-c40876cc.jpg', 'Someline ferrule kit (part 337), Makeronics '
          'breadboard station with ESP32 and relay (part 80), jumper wires, '
          'alligator leads'),
    631: ('16-12997ec7.jpg', 'Amazon mailer, a cable, LED strip, "Welcome to '
          'The Villages" acrylic sign, MDF sheets'),
}
OVERVIEW = (524, '01-70906dce.jpg')


def attach(loc_pk, path, comment, user):
    data = open(path, 'rb').read()
    dupe = Attachment.objects.filter(model_type='stocklocation', model_id=loc_pk,
                                     file_size=len(data)).first()
    if dupe:
        return dupe, False
    a = Attachment(model_type='stocklocation', model_id=loc_pk,
                   comment=comment[:250], upload_user=user)
    a.attachment.save(os.path.basename(path), ContentFile(data), save=True)
    return a, True


def new_description(loc, contents):
    base = loc.description.split(' Walked 20')[0].split(' VERIFIED EMPTY')[0]
    base = base.rstrip()
    if contents is None:
        return f'{base} VERIFIED EMPTY 2026-10-21 (photo attached).'
    return f'{base} {WALK}: {contents}. {UNRECORDED}'


def main():
    if not os.path.isdir(PHOTO_DIR):
        if not os.path.exists(TAR):
            print(f'no photos: push the tarball first ({TAR})')
            sys.exit(1)
        with tarfile.open(TAR) as t:
            t.extractall(PHOTO_DIR, filter='data')
    user = get_user_model().objects.filter(is_superuser=True).first()
    mode = 'COMMIT' if COMMIT else 'DRY RUN'
    print(f'=== LRD drawer walk phase A — {mode} ===\n')

    plan = [(pk, f, c) for pk, (f, c) in DRAWERS.items()]
    plan.append((OVERVIEW[0], OVERVIEW[1], 'OVERVIEW'))
    for pk, fname, contents in sorted(plan):
        loc = StockLocation.objects.get(pk=pk)
        path = os.path.join(PHOTO_DIR, fname)
        rows = StockItem.objects.filter(location=loc).count()
        if contents == 'OVERVIEW':
            desc = None
            comment = 'Bench overview 2026-10-21; Cab4-D1 is the open drawer'
        else:
            desc = new_description(loc, contents)
            comment = (f'{loc.name} as found 2026-10-21'
                       + ('; verified empty' if contents is None else ''))
        print(f'[{pk}] {loc.pathstring}  rows={rows}')
        print(f'      photo {fname} -> comment {comment!r}')
        if desc:
            print(f'      desc -> {desc}')
        if not COMMIT:
            continue
        if desc:
            StockLocation.objects.filter(pk=pk).update(description=desc)
        a, created = attach(pk, path, comment, user)
        # verify by re-read
        loc2 = StockLocation.objects.get(pk=pk)
        n_att = Attachment.objects.filter(model_type='stocklocation',
                                          model_id=pk).count()
        ok_desc = (desc is None) or (loc2.description == desc)
        print(f'      {"OK" if ok_desc else "DESC MISMATCH"}; attachment '
              f'{"added" if created else "already there"} '
              f'({a.attachment.name}), {n_att} on this location')
        if not ok_desc:
            print(f'      re-read: {loc2.description!r}')
    print('\nphase B (stock rows, commuting-tool landings) is a separate '
          'script, driven by counts from Scott.')


if __name__ == '__main__':
    main()
