"""Queue A, 2026-09-30: the two imageless parts on open POs raised 09-29.

  1265  1/2" Carbide Keyseat Cutter (PO-0186, Haas 03-3399) -- image URL is
        derived from the SKU (the Haas pattern; no page load needed).
  1266  NVIDIA T400 2GB, PNY VCNT400-PB (PO-0187, Amazon B09DG5B78Z) -- listing
        loaded in the agent Chrome, title "PNY NVIDIA T400"; landingImage
        data-old-hires and the first hiRes are the SAME id (41PyLEoHCIL), so no
        sibling-variant risk.

Same guards as img_attach_0927.py: magic bytes not content-type, size floor,
never overwrite, re-read after save.

Usage:  img_attach_0930.py [--commit]
"""
import argparse
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
from part.models import Part                      # noqa: E402

try:
    from PIL import Image
except ImportError:  # dims are informational only
    Image = None

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

HAAS = ("https://www.haastooling.com/content/dam/haas-tooling/ecommerce/products/"
        "{a}/{b}/image/{a}-{b}.jpg/_jcr_content/renditions/original./{a}-{b}.jpg")

TARGETS = [
    {"pk": 1265, "page": "https://www.haastooling.com/",
     "imgs": [HAAS.format(a="03", b="3399")]},
    {"pk": 1266, "page": "https://www.amazon.com/dp/B09DG5B78Z",
     "imgs": ["https://m.media-amazon.com/images/I/41PyLEoHCIL._AC_SL1200_.jpg",
              "https://m.media-amazon.com/images/I/41PyLEoHCIL._AC_.jpg"]},
]

MAGIC = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png", b"RIFF": "webp", b"GIF8": "gif"}
MIN_IMAGE_BYTES = 8192


def sniff(data):
    for m, ext in MAGIC.items():
        if data.startswith(m):
            if ext == "webp" and data[8:12] != b"WEBP":
                continue
            return ext
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


ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

got = []
for t in TARGETS:
    p = Part.objects.filter(pk=t["pk"]).first()
    if not p:
        print(f"?? {t['pk']}: no such part")
        continue
    print(f"-- {t['pk']}: {p.name[:70]} | desc: {(p.description or '')[:110]}")
    if p.image:
        print(f"=  {t['pk']}: already has an image ({p.image.name}) -- left alone")
        continue
    for url in t["imgs"]:
        status, data, ctype = get(url, t["page"])
        ext = sniff(data) if status == 200 else None
        if not ext:
            print(f"   miss status={status} {ctype} {len(data)}B  {url[-60:]}")
            continue
        if len(data) < MIN_IMAGE_BYTES:
            print(f"   miss {len(data)}B below floor  {url[-60:]}")
            continue
        t.update(ext=ext, data=data, sha=hashlib.sha256(data).hexdigest(), url=url)
        got.append(t)
        print(f"ok {t['pk']}: {ext} {len(data)//1024}KB {dims(data)} sha={t['sha'][:12]}  {url[-60:]}")
        break
    else:
        print(f"!! {t['pk']}: no candidate URL produced an image")

written = failed = 0
if a.commit:
    for g in got:
        p = Part.objects.get(pk=g["pk"])
        p.image.save(f"part_{g['pk']}.{g['ext']}", ContentFile(g["data"]), save=True)
        fresh = Part.objects.get(pk=g["pk"])
        if fresh.image:
            print(f"+  {g['pk']}: {fresh.image.name}")
            written += 1
        else:
            print(f"!! {g['pk']}: save reported success but the row is still empty")
            failed += 1

print(f"\nfetched={len(got)} images_written={written} failed_verify={failed}"
      f"{'  (DRY RUN)' if not a.commit else ''}")
allp = Part.objects.count()
have = Part.objects.exclude(image="").exclude(image__isnull=True).count()
print(f"coverage: {have}/{allp} parts have an image")
