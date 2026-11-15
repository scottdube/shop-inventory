#!/usr/bin/env python3
"""Overnight 2026-11-15 queue A: the seven imageless parts on open PO-0296..PO-0302.

All seven were created by po_1114_2240_ali_bench_zipbags.py on 11-14 22:4x.
Sources were read tonight in the agent Chrome (signed in):

  - AliExpress (#1533-#1538): order-detail page per order, one line each, the
    order-line title matched the part's `orig:` description and the SKU text
    matched the supplier-part SKU suffix. Thumbnail = CSS background-image on
    `.order-detail-item-content-img` (ali_images.py HARVEST NOTE); the trailing
    `_220x220.<ext>` is stripped for the original. Item URL = the anchor around
    that thumbnail, written to SupplierPart.link only while it is empty.
  - Amazon (#1539): /dp/B09M9VXXN1, first "hiRes" URL, the /W/<experiment>/
    path segment dropped (it is an A/B test prefix, the bare /images/I/ URL is
    the canonical CDN path). Supplier link already set by the PO script.

Rejected: the listing galleries. Three of these listings cover several widths
or pack sizes; the order-line thumbnail is the photo of the variant bought.

Bytes are fetched here on the Mini (both CDNs are undefended, task file
2026-08-24) and converted to JPEG because ae-pic serves WebP from .jpg URLs.
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
ALI = "https://ae-pic-a1.aliexpress-media.com/kf/"

# pk, sku prefix, name must contain, image url, item url (None = leave link), tag
ROWS = [
    (1533, "8216790551625753", "25mm", ALI + "Safd7e65e441b4b22829d9ee239ebcd55D.jpg",
     "https://www.aliexpress.com/item/3256808747262747.html", "ali"),
    (1534, "8216790551645753", "12mm", ALI + "H91934a3304304653b1a18a96f14d09369.jpg",
     "https://www.aliexpress.com/item/3256802521810770.html", "ali"),
    (1535, "8216790551705753", "5mm", ALI + "S56a61779ac6741d0bd43929865a09a27v.jpg",
     "https://www.aliexpress.com/item/3256806224120089.html", "ali"),
    (1536, "8216790551665753", "TP01", ALI + "S01d3c713211341e5968b18e8ed7c9c7f2.jpg",
     "https://www.aliexpress.com/item/3256808305890378.html", "ali"),
    (1537, "8216790551685753", "MY-065", ALI + "S61bc7965f0d643e3bac332329766076bD.jpg",
     "https://www.aliexpress.com/item/3256807536665597.html", "ali"),
    (1538, "8216790551725753", "KAISI", ALI + "S7be6ea28f8d6468880fc19812f696a7cF.png",
     "https://www.aliexpress.com/item/3256805970154427.html", "ali"),
    (1539, "B09M9VXXN1", "Zip Bag 6x9",
     "https://m.media-amazon.com/images/I/51P9MvVB3KL._AC_SL1500_.jpg", None, "amz"),
]

written = 0
for pk, sku, name_has, url, item, tag in ROWS:
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"?? {pk}: no such part -- skipped")
        continue
    if name_has not in p.name:
        print(f"!! {pk}: name {p.name!r} lacks {name_has!r} -- skipped")
        continue
    sps = [sp for sp in p.supplier_parts.all() if sp.SKU.startswith(sku)]
    if len(sps) != 1:
        print(f"!! {pk}: expected one supplier part for {sku}, found {len(sps)} -- skipped")
        continue
    sp = sps[0]
    if PLACEHOLDER in url:
        print(f"XX {pk}: placeholder hash -- rejected")
        continue

    if p.image:
        print(f"=  {pk}: already has an image ({p.image.name}) -- left alone")
    else:
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

    if item is None:
        continue
    if sp.link:
        print(f"=  sp {sp.pk}: link already set ({sp.link}) -- left alone")
    elif COMMIT:
        SupplierPart.objects.filter(pk=sp.pk, link__isnull=True).update(link=item)
        SupplierPart.objects.filter(pk=sp.pk, link="").update(link=item)
        print(f"sp {sp.pk} link now: {SupplierPart.objects.get(pk=sp.pk).link or '-'}")
    else:
        print(f"~  sp {sp.pk}: WOULD set link {item} (DRY RUN)")

print(f"images written this run: {written}")
act = Part.objects.filter(active=True)
have = act.exclude(image="").exclude(image__isnull=True).count()
print(f"coverage: {have}/{act.count()} active parts have an image")
