"""Attach Part.image from CDN URLs, fetched on the Mini.

Shape: BROWSER for the URL, MINI for the bytes. The product PAGES are defended
(Amazon challenges the Mini; Mouser serves an Akamai block even to a real
driven Chrome) but the image CDNs are not -- measured repeatedly, and measured
again tonight. That makes the laptop-fetch-then-scp dance unnecessary for
bytes, while keeping the browser as the only thing that reads a product page.

Guards, each of which has gone wrong on this install once already:
  * never overwrite a non-empty image slot -- a stock photo must not eat a
    bench photo of the actual unit;
  * verify by MAGIC BYTES, not by HTTP status -- a 200 with an HTML body is
    exactly what a defended host returns, and that is how a 43-byte Amazon
    placeholder got attached before;
  * verify the write by RE-READING the row -- .save() here has reported
    success and written nothing.

Usage:  img_attach_0919.py [--commit]
"""
import argparse
import os
import sys
import urllib.request

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.core.files.base import ContentFile  # noqa: E402
from part.models import Part                    # noqa: E402

# pk -> (url, evidence this is the right photo for this part)
JOBS = {
    1214: ("https://m.media-amazon.com/images/I/51NN+4SP8wL._AC_SL1500_.jpg",
           "ASIN B07FFNTLJD live, productTitle 'Ubiquiti Networks UniFi nanoHD "
           "Internal 1733Mbit/s Power Over Ethernet'; PO-0175 2026-09-18"),
    1216: ("https://m.media-amazon.com/images/I/61y6eV3GixL._AC_SL1500_.jpg",
           "ASIN B0FH6L2HJR live, productTitle '8K Mini DisplayPort to "
           "DisplayPort 1.4 Adapter 2 Pack'; PO-0177 2026-09-18"),
    1213: ("https://m.media-amazon.com/images/I/71-rF3-IXQL._AC_SL1500_.jpg",
           "ASIN B00MH4QKP6 live, productTitle 'Amazon Basics 12-Pack D Cell "
           "Alkaline Batteries, 1.5 Volt'"),
    1215: ("https://i.ebayimg.com/images/g/5VoAAeSwkzpqou7z/s-l1600.jpg",
           "eBay item 398401022842 og:title 'NVIDIA T400 4GB GDDR6 Low Profile "
           "GPU 3x Mini DisplayPort'; PO-0176 2026-09-18"),
}

MAGIC = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png", b"RIFF": "webp", b"GIF8": "gif"}

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

ok = skipped = bad = failed = 0
for pk, (url, why) in sorted(JOBS.items()):
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"?? {pk}: no such part")
        bad += 1
        continue
    if p.image:
        print(f"=  {pk}: already has an image ({p.image.name}) -- left alone")
        skipped += 1
        continue

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            ctype = r.headers.get("Content-Type", "")
    except Exception as e:  # noqa: BLE001
        print(f"!! {pk}: fetch failed -- {str(e)[:90]}")
        bad += 1
        continue

    ext = next((v for k, v in MAGIC.items() if data.startswith(k)), None)
    if not ext or len(data) < 4000:
        print(f"!! {pk}: NOT an image -- {len(data)}B ctype={ctype!r} "
              f"head={data[:16]!r}  (refused, nothing written)")
        bad += 1
        continue

    print(f"{'+' if a.commit else '~'}  {pk}: {len(data)//1024}KB {ext} "
          f"-- {p.name[:56]}")
    print(f"      {why}")
    if not a.commit:
        continue

    p.image.save(f"part_{pk}.{ext}", ContentFile(data), save=True)
    fresh = Part.objects.get(pk=pk)
    if fresh.image:
        ok += 1
    else:
        print(f"!! {pk}: save reported success but the row is still empty")
        failed += 1

print(f"\nset={ok} skipped_already_had={skipped} refused={bad} failed_verify={failed}"
      f"{'  (DRY RUN)' if not a.commit else ''}")

act = Part.objects.filter(active=True)
have = act.exclude(image="").exclude(image__isnull=True).count()
allp = Part.objects.count()
allhave = Part.objects.exclude(image="").exclude(image__isnull=True).count()
print(f"coverage: {have}/{act.count()} active   |   {allhave}/{allp} all parts")
