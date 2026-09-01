"""Print name + link + IPN for the given pks. Read-only, one line each.

Exists because "what URL is actually stored on this part?" is a question the
image queue asks constantly, and guessing a vendor URL instead of reading the
stored one is the documented origin of several wrong-photo incidents.
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--pk", type=int, action="append", required=True)
a = ap.parse_args()

for pk in a.pk:
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"{pk}\t<no such part>")
        continue
    print(f"{pk}\t{p.name}\n\tlink: {p.link or '<none>'}\n\tIPN : {p.IPN or '<none>'}"
          f"\n\timage: {p.image.name if p.image else '<none>'}")
