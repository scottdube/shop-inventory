"""Rotate the relay-row part images so the printing on the relay reads upright.

Scott, 2026-11-04: "make sure if its possible the writing is not upside down
like on the relays it is easier to read right side up". The crops were taken
in the orientation the boards lay on the lid. Rotation per part is judged by
eye from the relay-can text (the largest legible marking on each board):

  1503 1-ch 5V   180   (JQC-3FF-S-Z upside down)
  1504 2-ch 5V   180
  1505 30A       90 cw (SLA-05VDC-SL-C read bottom-to-top)
  1507 3V        90 ccw (SRD-03VDC-SL-C read top-to-bottom)
  1506 FC-19 left alone: its relay text is already upright.

Only the part image is replaced. Existing attachments are left as they are.
Idempotent: an image already named *-upright.jpg is skipped.

    itq run scripts/upright_relay_thumbs.py            # dry run: /tmp/upright-sheet.jpg
    itq run scripts/upright_relay_thumbs.py --commit
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from io import BytesIO  # noqa: E402
from PIL import Image  # noqa: E402
from django.core.files.base import ContentFile  # noqa: E402
from part.models import Part  # noqa: E402

commit = "--commit" in sys.argv
ROT = {1503: Image.Transpose.ROTATE_180, 1504: Image.Transpose.ROTATE_180,
       1505: Image.Transpose.ROTATE_270,   # PIL rotates ccw: 270 ccw = 90 cw
       1507: Image.Transpose.ROTATE_90}

out = {}
for pk, t in ROT.items():
    p = Part.objects.get(pk=pk)
    if "upright" in p.image.name:
        print(f"{pk} already upright: {p.image.name}")
        continue
    im = Image.open(p.image.path).convert("RGB").transpose(t)
    out[pk] = im
    print(f"{pk} {p.name[:50]} {p.image.name} -> rotate {t.name}")

if out:
    sheet = Image.new("RGB", (820, 410 * ((len(out) + 1) // 2)), "white")
    for i, im in enumerate(out.values()):
        th = im.copy()
        th.thumbnail((400, 400))
        sheet.paste(th, ((i % 2) * 410, (i // 2) * 410))
    sheet.save("/tmp/upright-sheet.jpg", quality=80)
if not commit:
    raise SystemExit("DRY RUN - look at /tmp/upright-sheet.jpg, then --commit")

for pk, im in out.items():
    buf = BytesIO()
    im.save(buf, "JPEG", quality=88)
    p = Part.objects.get(pk=pk)
    p.image.save(f"hot1027-relay{pk}-upright.jpg", ContentFile(buf.getvalue()), save=True)

bad = [pk for pk in ROT if "upright" not in Part.objects.get(pk=pk).image.name]
for pk in ROT:
    print(pk, Part.objects.get(pk=pk).image.name)
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
