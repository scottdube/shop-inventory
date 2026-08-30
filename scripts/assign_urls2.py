"""Assign Part.image from an explicit pk -> URL table decided by a human-verified page.

Same contract as the 2026-08-29 assign_urls.py, restated because it is the whole
point of the script:

  * The URL table is NOT discovered here. Each entry was read off a page that was
    actually loaded and eyeballed in the browser, and the note says what made the
    match provable. A script that searches for its own URLs is how a $379
    magnetic encoder ends up as the photo of an enclosure kit.
  * **Verify by CONTENT, never by status code.** A defended host returns 200 with
    text/html; a 404 still writes a body. Magic bytes decide.
  * **Never overwrite a filled image slot.** A vendor stock photo must not eat a
    photo of the actual unit on the bench.
  * **Re-read the row after saving.** .save() on this install has reported
    success and written nothing (docs/TRAPS.md).
  * Refuse duplicate payloads: if two pks resolve to byte-identical images, that
    is a family photo leaking in, and both are dropped rather than half-trusted.

Runs on the Mini. Mouser is expected to fail here (it hotlink-blocks the Mini's
IP; measured 2026-08-29 as 13897 bytes of text/html) — that is why the failure
report names the content-type and first bytes instead of just a count.
"""
import argparse
import hashlib
import os
import sys
import urllib.error
import urllib.request

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.core.files.base import ContentFile  # noqa: E402
from part.models import Part                    # noqa: E402

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

# pk -> (url, referer, why-this-match-is-provable)
TABLE = {
    1149: (
        "https://m.media-amazon.com/images/I/61eHm+nv8dL._AC_SL1500_.jpg",
        "https://www.amazon.com/dp/B0BHY918CR",
        "hiRes from the live /dp/B0BHY918CR page; title 'uxcell Nitrile Rubber "
        "Round Seal Strip, 3mm(1/8in) Diameter' matches the part name",
    ),
    108: (
        "https://www.mouser.com/images/alps/images/RKJXT1F42001.jpg",
        "https://www.mouser.com/ProductDetail/688-RKJXT1F42001",
        "og:image filename is the exact MPN RKJXT1F42001, off the real "
        "ProductDetail page for our SKU 688-RKJXT1F42001",
    ),
}

MAGIC = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png", b"RIFF": "webp", b"GIF8": "gif"}


def sniff(data):
    for m, ext in MAGIC.items():
        if data.startswith(m):
            if ext == "webp" and data[8:12] != b"WEBP":
                continue
            return ext
    return None


ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

fetched, failed = {}, []
for pk, (url, ref, why) in sorted(TABLE.items()):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": ref,
        "Accept": "image/avif,image/webp,image/jpeg,image/png,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            ctype = r.headers.get("content-type", "?")
    except (urllib.error.URLError, OSError) as e:
        failed.append((pk, f"transport: {e}"))
        continue

    ext = sniff(data)
    if not ext:
        failed.append((pk, f"NOT AN IMAGE — ctype={ctype} bytes={len(data)} "
                           f"first16={data[:16]!r}"))
        continue
    fetched[pk] = (data, ext, len(data), hashlib.sha256(data).hexdigest())
    print(f"got {pk}: {ext} {len(data)//1024}KB ctype={ctype}")

# A repeated payload means one photo is standing in for two parts.
seen = {}
for pk, (_d, _e, _n, h) in fetched.items():
    seen.setdefault(h, []).append(pk)
dupes = {h: pks for h, pks in seen.items() if len(pks) > 1}
for h, pks in dupes.items():
    print(f"!! identical bytes for pks {pks} — family photo, dropping all")
    for pk in pks:
        fetched.pop(pk, None)
        failed.append((pk, "duplicate payload shared with " + str(pks)))

set_ok = skipped_filled = missing = verify_fail = 0
for pk, (data, ext, n, h) in sorted(fetched.items()):
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"?? {pk}: no such part")
        missing += 1
        continue
    if p.image:
        print(f"=  {pk}: already has an image ({p.image.name}) — left alone")
        skipped_filled += 1
        continue
    if not a.commit:
        print(f"~  {pk}: WOULD set {n//1024}KB .{ext} — {p.name[:55]}")
        continue

    p.image.save(f"part_{pk}.{ext}", ContentFile(data), save=True)
    fresh = Part.objects.get(pk=pk)
    if fresh.image:
        print(f"+  {pk}: {fresh.image.name} ({n//1024}KB) — {p.name[:55]}")
        set_ok += 1
    else:
        print(f"!! {pk}: save reported success but the row is still empty")
        verify_fail += 1

print(f"\nset={set_ok} skipped_already_had_image={skipped_filled} "
      f"missing_part={missing} failed_verify={verify_fail} "
      f"fetch_failed={len(failed)} {'(DRY RUN)' if not a.commit else ''}")
for pk, why in failed:
    print(f"  FAIL {pk}: {why}")

total = Part.objects.count()
have = Part.objects.exclude(image="").exclude(image__isnull=True).count()
print(f"coverage now: {have}/{total}")
