"""Queue A, 2026-09-11: the four imageless parts sitting on OPEN purchase orders.

pk 1185 (DisplayPort 1.2 to 2x DisplayPort MST Hub)  on PO-0165, ASIN B075754ZYC
pk 1186 (USB-C Right-Angle Adapter, male to female)  on PO-0166, ASIN B0H3JNGX1D
pk 1187 (Cable, USB-A to Micro-USB, 3 ft, USB 2.0)   on PO-0167, ASIN B07QB6KL85
pk 1188 (VSDISPLAY 12.6in Bar Monitor, 1920x515 IPS) on PO-0168, ASIN B0C3CSW624

All four were created 2026-09-10 by the PO sweeps and all four orders are still
PLACED, so these are exactly the case queue A prioritises: image the part BEFORE
the box lands, so receiving needs no extra step.

Why these are workable when the rest of the Amazon pool is not: the
16-of-16-delisted measurement that closed that pool on 2026-09-01 describes the
ASINs that existed THEN. An ASIN bought yesterday is live by construction — the
same escape hatch as pk 1173/1174/1176/1180/1181.

hiRes URLs read out of the signed-in browser's /dp/ page tonight, one same-origin
fetch per ASIN; the returned <title> is recorded beside each URL so the match
between the URL and the part it is about to be attached to is visible, not
assumed. This script only fetches, verifies and attaches.

Fetching happens HERE on the Mini, not on the laptop: m.media-amazon.com serves
the Mini real JPEGs (measured 2026-08-29/30, re-confirmed by the 09-10 run),
and one hop beats three. Only the product PAGE is defended, which is why the
URLs come from the browser.

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
    (1185, "B075754ZYC",
     "https://m.media-amazon.com/images/I/51-n0cQXt1L._AC_SL1200_.jpg",
     "Monoprice DisplayPort 1.2 to DisplayPort Multi-Stream Transport (MST) Hub"),
    (1186, "B0H3JNGX1D",
     "https://m.media-amazon.com/images/I/611VhJolrkL._AC_SL1500_.jpg",
     "Vanjua 4 Pack 90 Degree USB-C Male to Female Adapter, Right Angle 10Gbps"),
    (1187, "B07QB6KL85",
     "https://m.media-amazon.com/images/I/51EzkvBO3pL._SL1200_.jpg",
     "Amazon Basics 5-Pack USB-A to Micro USB Charging Cable, 480Mbps"),
    (1188, "B0C3CSW624",
     "https://m.media-amazon.com/images/I/61vzM5rUf8L._AC_SL1500_.jpg",
     "VSDISPLAY 12.6'' IPS LCD Screen Monitor 1920x515 as PC Secondary screen"),
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
