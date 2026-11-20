#!/usr/bin/env python3
"""Overnight 2026-11-20 queue A: the one imageless part on an open PO.

Part #1541 (ST-Link V2 clone, PO-0304, Amazon B07SQV6VLZ), created by
po_1119_2240_hiletgo_stlink.py on 11-19 22:4x. Source read tonight in the agent
Chrome (signed in): /dp/B07SQV6VLZ, title matched the part's `orig:` text
verbatim, first "hiRes" URL (= #landingImage data-old-hires), with the
/W/<experiment>/ A/B prefix dropped as in img_1115.py.

Same shape as img_1115.py: bytes fetched on the Mini (CDN undefended, task file
2026-08-24), converted to JPEG, never overwrites, dry run unless --commit,
re-read after save (docs/TRAPS.md: silent no-op saves).
"""
import hashlib
import io
import os
import sys
import urllib.request

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.core.files.base import ContentFile  # noqa: E402
from part.models import Part  # noqa: E402
from PIL import Image  # noqa: E402

COMMIT = "--commit" in sys.argv
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
MIN_PX = 300

ROWS = [
    (1541, "B07SQV6VLZ", "ST-Link",
     "https://m.media-amazon.com/images/I/61Bxk48MNDL._AC_SL1500_.jpg", "amz"),
]

written = 0
for pk, sku, name_has, url, tag in ROWS:
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"?? {pk}: no such part -- skipped")
        continue
    if name_has not in p.name:
        print(f"!! {pk}: name {p.name!r} lacks {name_has!r} -- skipped")
        continue
    if len([sp for sp in p.supplier_parts.all() if sp.SKU == sku]) != 1:
        print(f"!! {pk}: expected one supplier part {sku} -- skipped")
        continue
    if p.image:
        print(f"=  {pk}: already has an image ({p.image.name}) -- left alone")
        continue
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        raw = urllib.request.urlopen(req, timeout=30).read()
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as e:  # noqa: BLE001
        print(f"XX {pk}: fetch/decode failed: {e}")
        continue
    w, h = img.size
    print(f"{pk} fetched {len(raw)//1024}KB {img.format} {w}x{h} "
          f"sha={hashlib.sha256(raw).hexdigest()[:12]} {p.name[:50]!r}")
    if min(w, h) < MIN_PX:
        print(f"XX {pk}: {w}x{h} below {MIN_PX}px -- rejected")
        continue
    if COMMIT:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=90)
        p.image.save(f"part_{pk}_{tag}.jpg", ContentFile(buf.getvalue()), save=True)
        fresh = Part.objects.get(pk=pk)
        if fresh.image:
            written += 1
            print(f"written {pk}: {fresh.image.name}")
        else:
            print(f"!! {pk}: save reported success but the row is still empty")
    else:
        print(f"~  {pk}: WOULD set image (DRY RUN)")

print(f"images written this run: {written}")
act = Part.objects.filter(active=True)
have = act.exclude(image="").exclude(image__isnull=True).count()
print(f"coverage: {have}/{act.count()} active parts have an image")
