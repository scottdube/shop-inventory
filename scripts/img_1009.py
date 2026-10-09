#!/usr/bin/env python3
"""Overnight 2026-10-09 queue A: Einstar Vega 3D scanner, part #1379.

Inflow since the 10-08 probe (HWM 1378) was three parts, filed by Scott's
2026-10-08 Florida packing session:

  1379  Shining 3D Einstar Vega  Amazon B0DL5L2MJH  -> hiRes read in the agent
        Chrome tonight from amazon.com/dp/B0DL5L2MJH (title verbatim 'Shining 3D
        Einstar Vega Wireless 3D Scanner ...', no challenge):
        https://m.media-amazon.com/images/I/61j5xCahGmL._SL1500_.jpg
  1380  BDM frame               no supplier part, no link  -> camera job
  1381  Soldering fume fan, shop-made                      -> camera job

The 21 imageless eBay tooling rows #1347-#1367 stay closed: TRAPS 2026-10-06
('eBay listings expire') already measured 19 of 31 links as 'Discover error'
and 333668081662 as a redirect to a different product. Re-measured tonight by
mistake before the grep came back; same result, 20 Discover error + the
micrometer redirect.

Standing shape (TRAPS 2026-10-06): URL read in Chrome on the laptop, CDN bytes
fetched here on the Mini. Never overwrites an existing image. Dry run by
default; --commit writes and re-reads.
"""
import hashlib
import io
import os
import ssl
import sys
import urllib.error
import urllib.request

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.core.files.base import ContentFile  # noqa: E402
from part.models import Part  # noqa: E402

try:
    from PIL import Image
except ImportError:
    Image = None

COMMIT = "--commit" in sys.argv
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
MIN_BYTES = 8192

TARGETS = [
    {"pk": 1379, "sku": "B0DL5L2MJH", "name_has": "Einstar Vega",
     "page": "https://www.amazon.com/dp/B0DL5L2MJH",
     "imgs": ["https://m.media-amazon.com/images/I/61j5xCahGmL._SL1500_.jpg",
              "https://m.media-amazon.com/images/I/41+jvwB0OZL.jpg"]},
]

MAGIC = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png", b"GIF8": "gif"}


def sniff(data):
    for m, ext in MAGIC.items():
        if data.startswith(m):
            return ext
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    return None


def dims(data):
    if not Image:
        return "?"
    try:
        w, h = Image.open(io.BytesIO(data)).size
        return f"{w}x{h}"
    except Exception as e:  # noqa: BLE001
        return f"unreadable({e.__class__.__name__})"


def get(url, referer):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer": referer,
        "Accept": "image/png,image/jpeg,image/webp,image/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=40,
                                    context=ssl.create_default_context()) as r:
            return r.status, r.read(), r.headers.get("content-type", "?")
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get("content-type", "?")
    except (urllib.error.URLError, OSError) as e:
        return None, str(e).encode(), "?"


got = []
for t in TARGETS:
    p = Part.objects.filter(pk=t["pk"]).first()
    if not p:
        print(f"?? {t['pk']}: no such part")
        continue
    if t["name_has"] not in p.name:
        print(f"!! {t['pk']}: name {p.name!r} lacks {t['name_has']!r} -- skipped")
        continue
    skus = {sp.SKU for sp in p.supplier_parts.all()}
    if t["sku"] not in skus:
        print(f"!! {t['pk']}: supplier SKUs {skus} lack {t['sku']} -- skipped")
        continue
    if p.image:
        print(f"=  {t['pk']}: already has an image ({p.image.name}) -- left alone")
        continue
    for url in t["imgs"]:
        status, data, ctype = get(url, t["page"])
        ext = sniff(data) if status == 200 else None
        if not ext:
            print(f"   miss {t['pk']} status={status} {ctype} {len(data)}B  {url[-60:]}")
            continue
        if len(data) < MIN_BYTES:
            print(f"   miss {t['pk']} {len(data)}B below floor  {url[-60:]}")
            continue
        t.update(ext=ext, data=data, sha=hashlib.sha256(data).hexdigest(), url=url)
        got.append(t)
        print(f"ok {t['pk']}: {ext} {len(data)//1024}KB {dims(data)} "
              f"sha={t['sha'][:12]}  {p.name[:48]}")
        break
    else:
        print(f"!! {t['pk']}: no candidate URL produced an image  ({p.name[:48]})")

written = failed = 0
if COMMIT:
    for g in got:
        p = Part.objects.get(pk=g["pk"])
        p.image.save(f"part_{g['pk']}.{g['ext']}", ContentFile(g["data"]), save=True)
        fresh = Part.objects.get(pk=g["pk"])
        if fresh.image:
            written += 1
            print(f"written {g['pk']}: {fresh.image.name}")
        else:
            print(f"!! {g['pk']}: save reported success but the row is still empty")
            failed += 1

print(f"\ntargets={len(TARGETS)} fetched={len(got)} images_written={written} "
      f"failed_verify={failed}{'' if COMMIT else '  (DRY RUN)'}")
act = Part.objects.filter(active=True)
have = act.exclude(image="").exclude(image__isnull=True).count()
print(f"coverage: {have}/{act.count()} active parts have an image")
