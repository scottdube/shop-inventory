"""Attach Part.image from CDN URLs, fetched on the Mini.  2026-09-20.

Same shape as img_attach_0919.py: BROWSER for the URL, MINI for the bytes.
Guards unchanged and each was paid for once -- never overwrite a non-empty
slot, accept on MAGIC BYTES not HTTP status, verify the write by re-reading
the row.

Tonight's pool is ONE row, and that is a supply fact rather than a method
fact: the 2026-09-19 census left AliExpress 4 + eBay 5 behind sessions and
everything else camera-only, and the only handle to arrive since is pk 1238
from PO-0178.  Identity here is an EXACT match, not a judgement: the eBay
item id 227521676914 is the SupplierPart SKU verbatim, and the listing title
("Science Fair 75 In 1 Electronic Project Kit - Radio Shack Wood - 28-247")
is the part name.  s-l1600 is requested first because eBay's size token is a
resize directive; s-l400 is the fallback the og:image actually advertises.

Usage:  img_attach_0920.py [--commit]
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

# pk -> ([urls, best first], evidence this is the right photo for this part)
JOBS = {
    1238: (["https://i.ebayimg.com/images/g/YCsAAeSwvd5qqFRB/s-l1600.jpg",
            "https://i.ebayimg.com/images/g/YCsAAeSwvd5qqFRB/s-l400.jpg"],
           "eBay item 227521676914 == SupplierPart SKU verbatim; listing title "
           "'Science Fair 75 In 1 Electronic Project Kit - Radio Shack Wood - "
           "28-247 NICE!'; PO-0178, read from the public item page 2026-09-20"),
}

MAGIC = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png", b"RIFF": "webp", b"GIF8": "gif"}

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

ok = skipped = bad = failed = 0
for pk, (urls, why) in sorted(JOBS.items()):
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"?? {pk}: no such part")
        bad += 1
        continue
    if p.image:
        print(f"=  {pk}: already has an image ({p.image.name}) -- left alone")
        skipped += 1
        continue

    data = ext = None
    for url in urls:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
                ctype = r.headers.get("Content-Type", "")
        except Exception as e:  # noqa: BLE001
            print(f"   {pk}: {url[-12:]} fetch failed -- {str(e)[:70]}")
            continue
        e2 = next((v for k, v in MAGIC.items() if body.startswith(k)), None)
        if not e2 or len(body) < 4000:
            print(f"   {pk}: {url[-12:]} NOT an image -- {len(body)}B "
                  f"ctype={ctype!r} head={body[:16]!r}")
            continue
        data, ext, chosen = body, e2, url
        break

    if data is None:
        print(f"!! {pk}: no usable bytes from any URL (refused, nothing written)")
        bad += 1
        continue

    print(f"{'+' if a.commit else '~'}  {pk}: {len(data)//1024}KB {ext} "
          f"from {chosen.rsplit('/', 1)[-1]} -- {p.name[:50]}")
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
