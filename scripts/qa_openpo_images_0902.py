"""Queue A: images for the three parts sitting on OPEN purchase orders.

These are the "parts on open POs jump the queue" case -- goods in transit, so the
picture should be on the part before the box lands and someone has to identify
it by name alone.

Why these three exist at all when the Amazon pool was closed 2026-09-01: that
closure measured 16 ASINs and found 16 delisted. It was a statement about THAT
SET. Parts 1166-1168 were created afterwards, from POs raised the same day, and
their listings are live -- confirmed in the browser tonight, each page returning
a real productTitle matching the part name.

URLS ARE DECIDED BY HAND, NOT SEARCHED. Each hiRes URL below was read out of the
`"hiRes"` field of its own /dp/<ASIN> page in the signed-in browser. The script
only fetches and checks; it never guesses a URL or matches on a search result,
which is the step that produced every wrong photo this queue has attached.

Verification is by CONTENT, never status code:
  * JPEG magic bytes, not Content-Type (a defended host returns 200 text/html)
  * a size floor, because the legacy /images/P/ path serves a 43-byte placeholder
  * sha256 across the batch, because one shared "series representation" photo
    landing on three different parts is the failure that looks like success
  * never overwrite a filled image slot -- a bench photo outranks a stock photo
  * re-read the row after save; .save() has reported success and written nothing
"""
import argparse
import hashlib
import os
import sys
import urllib.request

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.core.files.base import ContentFile  # noqa: E402
from part.models import Part  # noqa: E402

# pk, ASIN, hiRes URL read by hand from the product page, expected title fragment
TARGETS = [
    (1166, "B0FD2MGBZV",
     "https://m.media-amazon.com/images/I/7189IOQQ-nL._AC_SL1500_.jpg",
     "Battery Cable Crimper"),
    (1167, "B0FT8BQNVS",
     "https://m.media-amazon.com/images/I/81TD2maYtIL._AC_SL1500_.jpg",
     "6 AWG Battery Cable"),
    (1168, "B0DCVTTXMJ",
     "https://m.media-amazon.com/images/I/71WkxZChdqL._AC_SL1500_.jpg",
     "Battery Cleaning Brush"),
]

MIN_BYTES = 20_000

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

fetched = []
for pk, asin, url, label in TARGETS:
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"?? {pk}: no such part")
        continue
    if p.image:
        print(f"=  {pk}: already has an image ({p.image.name}) — left alone")
        continue

    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            data = r.read()
            status = r.status
    except Exception as e:  # noqa: BLE001
        print(f"!! {pk} {asin}: fetch failed — {e}")
        continue

    if not data.startswith(b"\xff\xd8\xff"):
        print(f"!! {pk} {asin}: status={status} but {len(data)}B is not a JPEG "
              f"(first bytes {data[:8]!r}) — rejected")
        continue
    if len(data) < MIN_BYTES:
        print(f"!! {pk} {asin}: {len(data)}B is below the {MIN_BYTES}B floor — "
              f"placeholder, rejected")
        continue

    digest = hashlib.sha256(data).hexdigest()
    fetched.append((pk, asin, data, digest, label, p))
    print(f"ok {pk} {asin}: status={status} {len(data)//1024}KB jpeg sha={digest[:12]} | {label}")

# One photo shared across parts means the vendor served a family/series render.
seen = {}
dupes = set()
for pk, asin, data, digest, label, p in fetched:
    if digest in seen:
        dupes.add(digest)
        print(f"!! sha collision: pk {seen[digest]} and pk {pk} share a photo — "
              f"both rejected, that is a series render not a product photo")
    seen[digest] = pk

writes = [t for t in fetched if t[3] not in dupes]

print()
set_ok = failed = 0
for pk, asin, data, digest, label, p in writes:
    name = f"part_{pk}_{asin}.jpg"
    if not a.commit:
        print(f"~  {pk}: WOULD set {name} ({len(data)//1024}KB) — {p.name[:52]}")
        continue
    p.image.save(name, ContentFile(data), save=True)
    fresh = Part.objects.get(pk=pk)
    if fresh.image:
        print(f"+  {pk}: {fresh.image.name} ({len(data)//1024}KB) — {p.name[:52]}")
        set_ok += 1
    else:
        print(f"!! {pk}: save reported success but the row is still empty")
        failed += 1

print(f"\nfetched={len(fetched)} rejected_dupe={len(fetched) - len(writes)} "
      f"set={set_ok} failed_verify={failed} {'(DRY RUN)' if not a.commit else ''}")

total = Part.objects.filter(active=True).count()
have = Part.objects.filter(active=True).exclude(image="").exclude(image__isnull=True).count()
print(f"active coverage now: {have}/{total}")
