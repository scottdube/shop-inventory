"""Queue A, 2026-09-25: the part number in the NAME is a handle.

probe_0924_0205.py found no inflow since 09-24 (max pk still 1260) and the only
open-PO imageless part is #1190, the Cults3D STL closed in TRAPS. So tonight
tried a route no run has bucketed: probe_0925_pn_in_name.py lists the 399
active imageless rows with no link and no supplier part -- the 09-22 "no handle
of any kind" bucket -- and 145 of them carry a part-number token in the NAME.

Most of the 145 are commodity parts (2N3904, 1N4148, JST-XH clones, WEIDU
terminal blocks) where no maker can be read off the record, so the 09-24
SKU-less guard (maker + model, each off the record) cannot pass: a photo of
somebody's 2N3904 is not a photo of ours. Only rows with a named maker AND a
maker-run single-product page carrying our identifier were fetched:

  1148  Adafruit QT Py RP2040 (PID 4900)     adafruit.com/product/4900, "Product ID: 4900"
  809   Adafruit TLV493D STEMMA QT            adafruit.com/product/4366, title carries TLV493D
  1236  Raspberry Pi 3 Model B (BCM2837)      raspberrypi.com 3-model-b page (not 3B+), BCM2837 on page
  930   MikroTik Metal 2SHPn                  mikrotik.com/product/RBMetal2SHPn, 2SHPn on page
  1070  Kill A Watt P4400.01 (P3)             p3international.com/products/p4400.html, P4400 on page
  1072  waveshare ESP32-S3-LCD-2.8C           waveshare esp32-s3-touch-lcd-2.8c.htm -- ONE page for
                                              both variants ("Options For Touch Function") and it
                                              carries ESP32-S3-LCD-2.8C verbatim; touch and non-touch
                                              boards are physically the same board

Rejected on the guard, with what eliminated them:
  1144  waveshare 4inch HDMI (C) -- the page at that slug is now a 720x720
        CAPACITIVE panel; ours is 800x480 resistive XPT2046. Different product
        reusing the name.
  1237  Stontronics DSA-13PFC-05 -- the official Pi 1/2/3 PSU page names
        neither Stontronics nor DSA-13PFC-05, and the official PSU was made by
        more than one vendor.
  797/798 Microchip -- product page og:image is an unlabelled asset render;
        not verifiable from the record, and a package render identifies nothing
        at the bench.
  923 Brother DK-11201, 1060 Watts P-412, 1047 WIMAXIT -- maker page 404 or
        store unavailable. Not chased further (one visit per site).

Not filling Part.link: these rows deliberately have no supplier, and a link
reads as a sourcing decision (same reasoning as img_attach_0924.py).

Each target lists image URLs best-first; the first that sniffs as an image
above the floor wins. Guards carried: magic bytes not content-type, size floor,
never overwrite, re-read after save.

Usage:  img_attach_0925.py [--commit]
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

TARGETS = [
    {"pk": 1148, "page": "https://www.adafruit.com/product/4900",
     # 4900-06 (the og:image) is a VIDEO still and 404s at 970x728; -13 is
     # the first gallery still in the page source.
     "imgs": ["https://cdn-shop.adafruit.com/970x728/4900-13.jpg",
              "https://cdn-shop.adafruit.com/480x360/4900-13.jpg"]},
    {"pk": 809, "page": "https://www.adafruit.com/product/4366",
     "imgs": ["https://cdn-shop.adafruit.com/970x728/4366-05.jpg",
              "https://www.adafruit.com/images/480x360/4366-05.jpg"]},
    {"pk": 1236, "page": "https://www.raspberrypi.com/products/raspberry-pi-3-model-b/",
     "imgs": ["https://images.prismic.io/rpf-products/877fb653-7b43-4931-9cee-977a22571f65_3b+Angle+2+refresh.jpg"]},
    {"pk": 930, "page": "https://mikrotik.com/product/RBMetal2SHPn",
     "imgs": ["https://cdn.mikrotik.com/web-assets/rb_images/773_hi_res.png",
              "https://cdn.mikrotik.com/web-assets/rb_images/773_tm.webp"]},
    {"pk": 1070, "page": "https://www.p3international.com/products/p4400.html",
     "imgs": ["https://www.p3international.com/products/images/main_p4400.jpg"]},
    {"pk": 1072, "page": "https://www.waveshare.com/esp32-s3-touch-lcd-2.8c.htm",
     "imgs": ["https://www.waveshare.com/media/catalog/product/cache/1/image/560x560/"
              "9df78eab33525d08d6e5fb8d27136e95/e/s/esp32-s3-touch-lcd-2.8c-1.jpg"]},
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
