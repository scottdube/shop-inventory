#!/usr/bin/env python3
"""Overnight 2026-11-06 queue A: the 7 imageless parts on open PO-0289/PO-0290.

  #1515 B0CW3FSBVT  Xiaomi Electric Precision Screwdriver (PO-0290). Title read
        tonight in the agent Chrome matches; hiRes URLs from the dp page HTML.
  #1509-#1514  Hakko FX971-010 kit + five T39 tips (PO-0289, order 1000204070).
        Each hakkousa.com page read tonight in the agent Chrome; its "Part Number"
        equals the supplier SKU for all six. Image = the page gallery "full" URL.

  #1509 TRAP: the part's link (set by po_1105_hakko_1000204070.py) points at
        fx-9701-standard-kit.html, which is the FX9701-011 CONVERSION kit
        ($149.97, iron + holder only), not the FX971-010 station kit that was
        ordered ($329.97). The image here comes from fx-971-soldering-station.html,
        whose Part Number reads FX971-010 and whose price matches the order line.
        The link itself is NOT changed by this script; it is reported for Scott.

Same shape as img_1105.py: URLs read in Chrome on the laptop, CDN bytes fetched
here on the Mini. Never overwrites an existing image. Dry run by default;
--commit writes and re-reads.
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
AMZ = "https://m.media-amazon.com/images/I/"
HK = "https://hakkousa.com/media/catalog/product/cache/df61d37d6011304edba9471c8a539a49/"
HKS = "https://hakkousa.com/"

TARGETS = [
    {"pk": 1515, "sku": "B0CW3FSBVT", "name_has": "Xiaomi",
     "page": "https://www.amazon.com/dp/B0CW3FSBVT",
     "imgs": [AMZ + "711Jc+lNyZL._AC_SL1500_.jpg", AMZ + "61CJT1b9U9L._AC_SL1500_.jpg"]},
    {"pk": 1509, "sku": "FX971-010", "name_has": "FX-971",
     "page": HKS + "fx-971-soldering-station.html",
     "imgs": [HK + "f/x/fx-971-station.jpg", HK + "f/x/fx-971_contents.jpg"]},
    {"pk": 1510, "sku": "T39-BC2535", "name_has": "T39-BC2535",
     "page": HKS + "t39-bc2535-bevel-tip.html",
     "imgs": [HK + "t/3/t39-bc2535_1.jpg", HK + "t/3/t39-bc2535.jpg"]},
    {"pk": 1511, "sku": "T39-BL02", "name_has": "T39-BL02",
     "page": HKS + "t39-bl02-conical-tip.html",
     "imgs": [HK + "t/3/t39-bl02_1.jpg", HK + "t/3/t39-bl02.jpg"]},
    {"pk": 1512, "sku": "T39-D12", "name_has": "T39-D12",
     "page": HKS + "t39-d12-chisel-tip.html",
     "imgs": [HK + "t/3/t39-d12.jpg"]},
    {"pk": 1513, "sku": "T39-D16", "name_has": "T39-D16",
     "page": HKS + "t39-d16-chisel-tip.html",
     "imgs": [HK + "t/3/t39-d16.jpg"]},
    {"pk": 1514, "sku": "T39-KU", "name_has": "T39-KU",
     "page": HKS + "t39-ku-knife-tip.html",
     "imgs": [HK + "t/3/t39-ku_1.jpg", HK + "t/3/t39-ku.jpg"]},
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
