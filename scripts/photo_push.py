#!/usr/bin/env python3
"""Push a photo into InvenTree. Never overwrites an existing part image.

Three cases, because a photo is not one kind of thing:

  --loc B3-R6C4     a scene. Several parts in one tote, or a drawer as found.
                    Goes on the LOCATION as an attachment. StockLocation has no
                    image field at all, so this is the only home it has, and it
                    is the right one: what the drawer looks like is a fact about
                    the drawer.

  --part N          a portrait. Attached to the part. If --primary is given AND
                    the part's image slot is empty, it also becomes the part
                    image. If the slot is already filled it stays filled and the
                    photo lands as an attachment instead - a vendor stock photo
                    and a photo of the actual unit on the bench are different
                    information and neither should silently eat the other.

Both can be given at once: the relay tote photo is evidence about the drawer AND
about each board in it.
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()

from common.models import Attachment          # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.core.files.base import ContentFile  # noqa: E402
from part.models import Part                  # noqa: E402
from stock.models import StockLocation        # noqa: E402


def attach(model_type, model_id, path, comment, user):
    data = open(path, 'rb').read()
    base = os.path.basename(path)
    dupe = Attachment.objects.filter(model_type=model_type, model_id=model_id,
                                     file_size=len(data)).first()
    if dupe:
        print(f'   = already attached to {model_type} {model_id} '
              f'({dupe.attachment.name})')
        return dupe
    a = Attachment(model_type=model_type, model_id=model_id, comment=comment[:250],
                   upload_user=user)
    a.attachment.save(base, ContentFile(data), save=True)
    print(f'   + attached to {model_type} {model_id}: {a.attachment.name} '
          f'({len(data)//1024}KB)')
    return a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', required=True)
    ap.add_argument('--loc', help='stock location name')
    ap.add_argument('--part', type=int, action='append', default=[],
                    help='part pk (repeatable)')
    ap.add_argument('--primary', action='store_true',
                    help='also use as the part image IF that slot is empty')
    ap.add_argument('--comment', default='')
    args = ap.parse_args()

    if not os.path.exists(args.file):
        print(f'no such file: {args.file}'); sys.exit(1)
    user = get_user_model().objects.filter(is_superuser=True).first()

    if args.loc:
        loc = StockLocation.objects.get(name=args.loc)
        print(f'{loc.name} (pk {loc.pk})')
        attach('stocklocation', loc.pk, args.file, args.comment, user)

    for pk in args.part:
        p = Part.objects.get(pk=pk)
        print(f'[{pk}] {p.name[:56]}')
        attach('part', pk, args.file, args.comment, user)
        if args.primary:
            if p.image:
                print(f'   ! image slot already holds {p.image} - LEFT ALONE')
            else:
                p.image.save(os.path.basename(args.file),
                             ContentFile(open(args.file, 'rb').read()), save=True)
                print(f'   * image slot was empty - set to {p.image}')


if __name__ == '__main__':
    main()
