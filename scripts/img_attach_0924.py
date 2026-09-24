"""Queue A, 2026-09-24: the one workable inflow row.

probe_0924_0205.py measured the pools: the only imageless part on an open PO is
#1190 (Cults3D STL, closed in TRAPS as a design nobody sells), and the only rows
created since the 09-23 run are the two Emporia Vue 3 leftover CTs from
add_emporia_cts.py:

  1259  Current Transformer 50A split-core, Emporia Vue branch sensor  -> ATTACH
  1260  Current Transformer 200A split-core, Emporia Vue mains sensor  -> NOT

Identity guard. These parts deliberately carry no supplier part and no SKU (the
kit ASIN B0C79PNK84 is an assortment), so the usual "page carries our identifier
verbatim" test has nothing to match. The substitute is maker + generation +
rating, all three read off the record: Emporia (maker), Vue 3 (the kit order in
the part notes), 50A branch. shop.emporiaenergy.com/products/50a-sensor-for-vue-
3-home-energy-monitor-single-sensor is the maker's own single-sensor page for
exactly that, SKU EMV3CT5-A-1; image = its first gallery slot, 50a-CT_1.jpg.

Rejected for #1260: Emporia's store sells no Gen-3 200A split-core clamp on its
own. The only rigid 200A listing is "Replacement Parts | GEN2 200A Sensor" -- a
different generation, and a picture of the wrong generation is the
name-the-part-off-the-part failure. The Vue 3 kit hero image shows the monitor
and sixteen clamps, not the mains clamp. Left empty: blank is honest.

Rejected: filling Part.link on #1259. Not a reorder item (a leftover), and the
record deliberately has no supplier; a link would read as a sourcing decision.

Guards carried from img_attach_0923.py: magic bytes not content-type, 2 KB
floor, never overwrite, re-read after save.

Usage:  img_attach_0924.py [--commit]
"""
import argparse
import hashlib
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

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

TARGETS = [
    {"pk": 1259,
     "page": "https://shop.emporiaenergy.com/products/50a-sensor-for-vue-3-home-energy-monitor-single-sensor",
     "img": "https://cdn.shopify.com/s/files/1/0311/1151/2109/files/50a-CT_1.jpg?v=1721681789"},
]

MAGIC = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png", b"RIFF": "webp", b"GIF8": "gif"}
MIN_IMAGE_BYTES = 2048


def sniff(data):
    for m, ext in MAGIC.items():
        if data.startswith(m):
            if ext == "webp" and data[8:12] != b"WEBP":
                continue
            return ext
    return None


def get(url, referer):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer": referer,
        "Accept": "image/png,image/jpeg,image/*;q=0.8"})
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
    if p.image:
        print(f"=  {t['pk']}: already has an image ({p.image.name}) -- left alone")
        continue
    status, data, ctype = get(t["img"], t["page"])
    ext = sniff(data) if status else None
    if not ext:
        print(f"!! {t['pk']}: status={status} {ctype} {len(data)}B -- not an image")
        continue
    if len(data) < MIN_IMAGE_BYTES:
        print(f"!! {t['pk']}: {len(data)}B -- degenerate, placeholder")
        continue
    t.update(ext=ext, data=data, sha=hashlib.sha256(data).hexdigest())
    got.append(t)
    print(f"ok {t['pk']}: {ext} {len(data)//1024}KB sha={t['sha'][:12]} | {p.name[:60]}")

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
