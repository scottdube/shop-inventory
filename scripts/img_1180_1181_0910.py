"""Queue A, 2026-09-10: the two imageless parts sitting on OPEN purchase orders.

pk 1180 (Power Cord Splitter, NEMA 5-15P to 2x 5-15R) on PO-0162, ASIN B00FRODUR4
pk 1181 (DisplayPort 1.2 to 2x HDMI MST Hub)          on PO-0163, ASIN B07575NBTV

Both were created 2026-09-09 by the PO sweep and both orders are still PLACED, so
these are exactly the case queue A prioritises: image the part BEFORE the box
lands, so receiving needs no extra step.

Why these are workable when the rest of the Amazon pool is not: the
16-of-16-delisted measurement that closed that pool on 2026-09-01 describes the
ASINs that existed THEN. An ASIN bought yesterday is live by construction. Same
escape hatch as pk 1173 (09-04), 1174 (09-06), 1176 (09-07).

hiRes URLs read out of the signed-in browser's /dp/ page tonight; the returned
productTitle matched the PO line verbatim in both cases, which is the check that
a URL belongs to the part it is about to be attached to. This script only
fetches, verifies and attaches.

Checks are the traps already paid for:
  * verify by CONTENT, not status — a defended host answers 200 with text/html;
  * a 2KB floor against the 43-byte `/images/P/<ASIN>` placeholder class;
  * never overwrite a filled slot — a stock photo must not eat a bench photo;
  * re-read the row after save, because .save() here has reported success and
    written nothing.
"""
import argparse
import gzip
import hashlib
import os
import ssl
import sys
import urllib.error
import urllib.request
import zlib

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.core.files.base import ContentFile  # noqa: E402
from part.models import Part                    # noqa: E402

TARGETS = [
    (1180, "B00FRODUR4",
     "https://m.media-amazon.com/images/I/51sQbNtoVXL._AC_SL1000_.jpg",
     "Power Cord Extension and Splitter, NEMA 5-15P to NEMA 5-15R x 2"),
    (1181, "B07575NBTV",
     "https://m.media-amazon.com/images/I/517h6x6oI3L._AC_SL1200_.jpg",
     "Monoprice 2-Port DisplayPort 1.2 to HDMI Multi-Stream Transport (MST) Hub"),
]

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
MAGIC = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png", b"RIFF": "webp"}
MIN_BYTES = 2048

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()


def get(url, referer=None):
    hdr = {"User-Agent": UA, "Accept": "image/avif,image/webp,*/*",
           "Accept-Language": "en-US,en;q=0.9", "Accept-Encoding": "gzip, deflate"}
    if referer:
        hdr["Referer"] = referer
    req = urllib.request.Request(url, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=40,
                                    context=ssl.create_default_context()) as r:
            raw, enc, ctype, status = (r.read(),
                                       (r.headers.get("content-encoding") or "").lower(),
                                       r.headers.get("content-type", "?"), r.status)
    except urllib.error.HTTPError as e:
        raw, enc, ctype, status = (e.read(),
                                   (e.headers.get("content-encoding") or "").lower(),
                                   e.headers.get("content-type", "?"), e.code)
    except (urllib.error.URLError, OSError) as e:
        return None, f"transport: {e}".encode(), "?"
    if enc == "gzip":
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
    elif enc == "deflate":
        try:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        except zlib.error:
            pass
    return status, raw, ctype


def sniff(data):
    for m, ext in MAGIC.items():
        if data.startswith(m):
            if ext == "webp" and data[8:12] != b"WEBP":
                continue
            return ext
    return None


attached = 0
for pk, asin, img, title in TARGETS:
    print()
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"!! no part {pk}")
        continue
    print(f"part {pk}: {p.name}")
    print(f"   listing title: {title}")
    if p.image:
        print(f"=  already has an image ({p.image.name}) — left alone")
        continue

    status, data, ctype = get(img, referer=f"https://www.amazon.com/dp/{asin}")
    print(f"   fetch: status={status} ctype={ctype} bytes={len(data)}")
    if status != 200:
        print("!! not 200 — leaving the slot empty")
        continue

    ext = sniff(data)
    if not ext:
        print(f"!! bytes are not an image (ctype said {ctype}) — "
              f"first 60: {data[:60]!r}")
        continue
    if len(data) < MIN_BYTES:
        print(f"!! {len(data)} bytes — placeholder class, refusing")
        continue

    sha = hashlib.sha256(data).hexdigest()
    print(f"   verified: {ext} {len(data)//1024}KB sha256={sha[:16]}")

    if not a.commit:
        print(f"~  WOULD set part_{pk}.{ext} on pk {pk} (DRY RUN)")
        continue

    p.image.save(f"part_{pk}.{ext}", ContentFile(data), save=True)
    fresh = Part.objects.get(pk=pk)
    if fresh.image:
        print(f"+  {pk}: {fresh.image.name} attached and VERIFIED by re-read")
        attached += 1
    else:
        print(f"!! {pk}: save reported success but the row is still empty")

print()
print(f"attached this run: {attached}")
active = Part.objects.filter(active=True)
print(f"active coverage now: "
      f"{active.exclude(image='').exclude(image__isnull=True).count()}/{active.count()}")
