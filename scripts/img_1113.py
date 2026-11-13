#!/usr/bin/env python3
"""Overnight 2026-11-13 queue A: the one imageless part on open PO-0293.

  #1532  Watch Crystal, mineral glass, double dome, 35.5 mm dia x 2.0 mm
         AliExpress order 8216522373115753 (PO-0293, created 11-12 16:43).

The order-detail page was read tonight in the agent Chrome (signed in, one
item, SKU text "Diameter 35.5mm, Thick 2.0mm", title matches the part's
`orig:` description). The thumbnail is the CSS background-image on
`.order-detail-item-content-img` (ali_images.py HARVEST NOTE); the trailing
`_220x220.jpg` is stripped for the original. Bytes are fetched here on the
Mini because the ae-pic CDN is undefended, and converted to JPEG because that
CDN serves WebP from a .jpg URL.

Also fills SupplierPart.link, which po_1112_1640_ali_watch_crystal.py left
empty: the item URL is the anchor around that same thumbnail. Only written if
the field is still empty.

Rejected: using the generic listing gallery instead. The listing covers
28-38.5 mm in three thicknesses; the order-line thumbnail is the photo
AliExpress attached to the variant actually bought.

Never overwrites an existing image. Dry run by default; --commit writes and
re-reads (docs/TRAPS.md: silent no-op saves).
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

from company.models import SupplierPart  # noqa: E402
from django.core.files.base import ContentFile  # noqa: E402
from part.models import Part  # noqa: E402
from PIL import Image  # noqa: E402

COMMIT = "--commit" in sys.argv
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
MIN_PX = 300
PLACEHOLDER = "Sf5a31ce867174aa7bf499352d6875ddc"  # delisted-item placeholder hash

PK = 1532
ORDER = "8216522373115753"
NAME_HAS = "Watch Crystal"
IMG = "https://ae-pic-a1.aliexpress-media.com/kf/S52fc6ba7258f4373b40dfb813fe14f0eE.jpg"
ITEM = "https://www.aliexpress.com/item/3256813200230570.html"

p = Part.objects.filter(pk=PK).first()
if not p:
    sys.exit(f"?? {PK}: no such part")
if NAME_HAS not in p.name:
    sys.exit(f"!! {PK}: name {p.name!r} lacks {NAME_HAS!r} -- stopped")
sps = [sp for sp in p.supplier_parts.all() if sp.SKU.startswith(ORDER)]
if len(sps) != 1:
    sys.exit(f"!! {PK}: expected one supplier part for order {ORDER}, found {len(sps)}")
sp = sps[0]
print(f"part {PK} {p.name!r} sp={sp.pk} sku={sp.SKU!r} link={sp.link or '-'}")

if PLACEHOLDER in IMG:
    sys.exit("XX placeholder hash -- rejected")

if p.image:
    print(f"=  {PK}: already has an image ({p.image.name}) -- left alone")
else:
    req = urllib.request.Request(IMG, headers={"User-Agent": UA})
    raw = urllib.request.urlopen(req, timeout=30).read()
    img = Image.open(io.BytesIO(raw))
    img.load()
    w, h = img.size
    print(f"fetched {len(raw)//1024}KB {img.format} {w}x{h} "
          f"sha={hashlib.sha256(raw).hexdigest()[:12]}")
    if min(w, h) < MIN_PX:
        sys.exit(f"XX {w}x{h} below {MIN_PX}px -- placeholder or thumbnail, rejected")
    if COMMIT:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=90)
        p.image.save(f"part_{PK}_ali.jpg", ContentFile(buf.getvalue()), save=True)
        fresh = Part.objects.get(pk=PK)
        if fresh.image:
            print(f"written {PK}: {fresh.image.name}")
        else:
            print(f"!! {PK}: save reported success but the row is still empty")
    else:
        print(f"~  {PK}: WOULD set image (DRY RUN)")

if sp.link:
    print(f"=  sp {sp.pk}: link already set ({sp.link}) -- left alone")
elif COMMIT:
    SupplierPart.objects.filter(pk=sp.pk, link__isnull=True).update(link=ITEM)
    SupplierPart.objects.filter(pk=sp.pk, link="").update(link=ITEM)
    fresh_sp = SupplierPart.objects.get(pk=sp.pk)
    print(f"sp {sp.pk} link now: {fresh_sp.link or '-'}")
else:
    print(f"~  sp {sp.pk}: WOULD set link {ITEM} (DRY RUN)")

act = Part.objects.filter(active=True)
have = act.exclude(image="").exclude(image__isnull=True).count()
print(f"coverage: {have}/{act.count()} active parts have an image")
