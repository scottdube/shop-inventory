"""Queue A, 2026-09-04: the one imageless part sitting on an open PO.

pk 1173 (PCF8574AP I2C expander) was created 2026-09-03 by PO-0158 and its ASIN
B0GF1Q1GNG is LIVE — which is why it is workable when the rest of the Amazon
pool is not. The 16-of-16-delisted measurement that closed that pool is a
statement about the ASINs that existed then, not about ones bought yesterday.

Method is the one the journal has used since 09-02 and it does not change: the
hiRes URL is read BY HAND out of the signed-in browser's /dp/ page (verified
there: ASIN present in the body, title carries "PCF8574AP" and "DIP-16"), and
this script only fetches, checks and attaches. The checks are the traps already
paid for:

  * verify by CONTENT, not status — a defended host answers 200 with text/html,
    so the bytes must sniff as a real image;
  * a 2KB floor against the 43-byte `/images/P/<ASIN>` placeholder class;
  * never overwrite a filled slot — a stock photo must not eat a bench photo;
  * re-read the row after save, because .save() on this install has reported
    success and written nothing.
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

PK = 1173
ASIN = "B0GF1Q1GNG"
IMG = "https://m.media-amazon.com/images/I/71og3w+Br+L._SL1500_.jpg"
REFERER = f"https://www.amazon.com/dp/{ASIN}"

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


p = Part.objects.filter(pk=PK).first()
if not p:
    sys.exit(f"no part {PK}")
print(f"part {PK}: {p.name}")
if p.image:
    sys.exit(f"=  already has an image ({p.image.name}) — left alone, nothing to do")

status, data, ctype = get(IMG, referer=REFERER)
print(f"fetch: status={status} ctype={ctype} bytes={len(data)}")
if status != 200:
    sys.exit(f"!! not 200 — leaving the slot empty")

ext = sniff(data)
if not ext:
    sys.exit(f"!! bytes are not an image (ctype said {ctype}) — "
             f"first 60: {data[:60]!r}")
if len(data) < MIN_BYTES:
    sys.exit(f"!! {len(data)} bytes — placeholder class, refusing")

sha = hashlib.sha256(data).hexdigest()
print(f"verified: {ext} {len(data)//1024}KB sha256={sha[:16]}")

if not a.commit:
    print(f"~  WOULD set part_{PK}.{ext} on pk {PK} (DRY RUN)")
    sys.exit(0)

p.image.save(f"part_{PK}.{ext}", ContentFile(data), save=True)
fresh = Part.objects.get(pk=PK)
if fresh.image:
    print(f"+  {PK}: {fresh.image.name} attached and VERIFIED by re-read")
else:
    sys.exit(f"!! {PK}: save reported success but the row is still empty")

active = Part.objects.filter(active=True)
print(f"active coverage now: "
      f"{active.exclude(image='').exclude(image__isnull=True).count()}/{active.count()}")
