"""Assign Part.image from an explicit pk -> URL table decided by a loaded page.

Same contract as assign_urls2.py (2026-08-30) — restated because it is the whole
point: the URL table is NOT discovered here. Each entry was read off a page that
was actually rendered in the browser, and the note records what makes the match
provable. A script that searches for its own URLs is how a $379 magnetic encoder
becomes the photo of an enclosure kit.

Guards, all load-bearing: verify by CONTENT not status code; never overwrite a
filled image slot; re-read the row after saving; drop byte-identical payloads
shared between pks (that is a family photo leaking in).

2026-09-01 entry:

  845 Digilent OpenScope MZ — digilent.com returns **403 to the Mini** (measured
  minutes earlier by img_from_link.py against the same stored link), so the page
  was opened in the browser instead, per CLAUDE.md's standing rule. It served a
  Cloudflare "Just a moment..." interstitial that cleared **on its own** — no
  challenge was solved and none was presented — and then rendered as
  "OpenScope MZ (Legacy) - Digilent Reference" with the body containing
  "OpenScope MZ".

  What makes the match provable is the image PATH, not a search rank:
  `/_media/reference/test-and-measurement/openscope-mz/openscope_mz_1.png` —
  the product's own slug, on the product's own reference page, 1000x855. There
  is no variant question here either: the OpenScope MZ is a one-of instrument,
  not a family with sizes, so the failure mode that closed Lakeshore and Canal
  Rubber (one photo standing in for parts that differ by a dimension) cannot
  apply.

  The CDN path is on the same host that 403'd, so this may still fail on the
  Mini — that is exactly the Amazon shape (defended product page, undefended
  CDN) and is worth measuring rather than assuming. If it fails, the fallback is
  scripts/fetch_local.py on the laptop.
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
    845: (
        "https://digilent.com/reference/_media/reference/test-and-measurement/"
        "openscope-mz/openscope_mz_1.png",
        "https://digilent.com/reference/test-and-measurement/openscope-mz/start",
        "image path carries the product slug openscope-mz and sits on the "
        "part's own stored reference page, which rendered as 'OpenScope MZ "
        "(Legacy) - Digilent Reference'; 1000x855, and the instrument is "
        "one-of so there is no variant to confuse",
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

seen = {}
for pk, (_d, _e, _n, h) in fetched.items():
    seen.setdefault(h, []).append(pk)
for h, pks in {h: p for h, p in seen.items() if len(p) > 1}.items():
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
