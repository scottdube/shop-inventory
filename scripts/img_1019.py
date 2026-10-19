#!/usr/bin/env python3
"""Overnight 2026-10-19 queue A: the three open-PO parts #1414, #1415, #1416.

The only imageless parts in the open-PO pool (PO-0264 from the 10-18 12:40
sweep, PO-0265 from the 10-18 22:40 sweep). Part HWM is 1416.

  1414  Amazon B0FHRGL3F2 -> hiRes read in the agent Chrome tonight from
        amazon.com/dp/B0FHRGL3F2 (title verbatim 'Wireless Lavalier Microphone
        for iPhone & Android, 2 Pack Mini Mic with USB-C/Lightning/USB-A
        Receiver ...', no challenge):
        https://m.media-amazon.com/images/I/61LR272449L._AC_SL1280_.jpg
  1415  Amazon B01AG56HYQ -> hiRes from amazon.com/dp/B01AG56HYQ (title
        verbatim 'Professional Grade Lavalier Clip On Microphone - Lav Mic ...
        3.5mm Tiny Shirt Microphone', page brand PowerDeWise):
        https://m.media-amazon.com/images/I/61OCx9oEXJL._AC_SL1280_.jpg
  1416  Amazon B0CP7QXWPN -> hiRes from amazon.com/dp/B0CP7QXWPN (title
        verbatim 'Hollyland Lark M2 Wireless Microphone ... (2TX + 3RX +
        Charging Case)'):
        https://m.media-amazon.com/images/I/61vXwLemjJL._AC_SL1500_.jpg

Part.link is set to the dp URL only where empty (same as #1410-#1413).

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
    {"pk": 1414, "sku": "B0FHRGL3F2", "name_has": "wireless lavalier",
     "page": "https://www.amazon.com/dp/B0FHRGL3F2",
     "imgs": ["https://m.media-amazon.com/images/I/61LR272449L._AC_SL1280_.jpg",
              "https://m.media-amazon.com/images/I/41qPkjC-RkL._AC_.jpg"]},
    {"pk": 1415, "sku": "B01AG56HYQ", "name_has": "wired lavalier",
     "page": "https://www.amazon.com/dp/B01AG56HYQ",
     "imgs": ["https://m.media-amazon.com/images/I/61OCx9oEXJL._AC_SL1280_.jpg",
              "https://m.media-amazon.com/images/I/41UjrRJb8VL._AC_.jpg"]},
    {"pk": 1416, "sku": "B0CP7QXWPN", "name_has": "Lark M2",
     "page": "https://www.amazon.com/dp/B0CP7QXWPN",
     "imgs": ["https://m.media-amazon.com/images/I/61vXwLemjJL._AC_SL1500_.jpg",
              "https://m.media-amazon.com/images/I/41C6hPvag5L._AC_.jpg"]},
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

written = failed = links = 0
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
        if not fresh.link:
            Part.objects.filter(pk=g["pk"], link__isnull=True).update(link=g["page"])
            Part.objects.filter(pk=g["pk"], link="").update(link=g["page"])
            if Part.objects.get(pk=g["pk"]).link == g["page"]:
                links += 1
                print(f"link set {g['pk']}: {g['page']}")
            else:
                print(f"!! {g['pk']}: link write did not land")

print(f"\ntargets={len(TARGETS)} fetched={len(got)} images_written={written} "
      f"links_set={links} failed_verify={failed}{'' if COMMIT else '  (DRY RUN)'}")
act = Part.objects.filter(active=True)
have = act.exclude(image="").exclude(image__isnull=True).count()
print(f"coverage: {have}/{act.count()} active parts have an image")
