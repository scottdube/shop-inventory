"""Queue A: harvest a product photo from a part's own `Part.link`, on the Mini.

Every image method this queue has had so far starts from a SupplierPart SKU and
then has to *find* the product page — and finding it is the step that produced
every wrong photo in this project's history (Tormach's fuzzy search, Lakeshore's
200-with-Page-Not-Found, DigiKey's onsemi result for a hand-built C&K URL).

`Part.link`, where it is set, skips that step entirely: it is the page, recorded
when the part was created. So this fetches the stored URL and never searches.

Still verified by CONTENT, because a stored link can rot:
  * the page must return 200 with a real `<title>`
  * the title must share real tokens with the part name
  * the image must pass a magic-byte sniff and a degenerate-size floor

Writes part_<pk>.<ext> + images.tar for `set_images.py --tar`; attaches nothing
itself.

Usage:  itq run scripts/img_from_link.py --pk 845 [--pk ...]
"""
import argparse
import hashlib
import gzip
import os
import re
import ssl
import sys
import tarfile
import urllib.error
import urllib.request
import zlib

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
MAGIC = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png", b"RIFF": "webp", b"GIF8": "gif"}
MIN_IMAGE_BYTES = 2048
STOPWORDS = {"the", "and", "for", "with", "kit", "set", "of", "in", "a"}


def sniff(data):
    for m, ext in MAGIC.items():
        if data.startswith(m):
            if ext == "webp" and data[8:12] != b"WEBP":
                continue
            return ext
    return None


def get(url, referer=None):
    hdr = {"User-Agent": UA,
           "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,*/*",
           "Accept-Language": "en-US,en;q=0.9",
           "Accept-Encoding": "gzip, deflate"}
    if referer:
        hdr["Referer"] = referer
    req = urllib.request.Request(url, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=40,
                                    context=ssl.create_default_context()) as r:
            raw, enc, status = r.read(), r.headers.get("content-encoding", ""), r.status
            ctype = r.headers.get("content-type", "?")
    except urllib.error.HTTPError as e:
        raw, enc, status = e.read(), e.headers.get("content-encoding", ""), e.code
        ctype = e.headers.get("content-type", "?")
    except (urllib.error.URLError, OSError) as e:
        return None, f"transport: {e}", "?"
    if (enc or "").lower() == "gzip":
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
    elif (enc or "").lower() == "deflate":
        try:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        except zlib.error:
            pass
    return status, raw, ctype


def tokens(s):
    return {t for t in re.findall(r"[a-z0-9]{3,}", s.lower()) if t not in STOPWORDS}


ap = argparse.ArgumentParser()
ap.add_argument("--pk", type=int, action="append", required=True)
ap.add_argument("--out", default="/tmp/link_images")
a = ap.parse_args()

os.makedirs(a.out, exist_ok=True)
got, bad = [], []

for pk in a.pk:
    p = Part.objects.filter(pk=pk).first()
    if not p:
        bad.append((pk, "no such part"))
        continue
    if p.image:
        bad.append((pk, f"already has an image ({p.image.name}) — left alone"))
        continue
    link = (p.link or "").strip()
    if not link:
        bad.append((pk, "no link stored"))
        continue

    status, body, ctype = get(link)
    if status is None:
        bad.append((pk, str(body)))
        continue
    if status != 200:
        bad.append((pk, f"page status={status} bytes={len(body)} — link may have rotted"))
        continue

    html = body.decode("utf8", "replace")
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    title = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    shared = tokens(p.name) & tokens(title)
    if not shared:
        bad.append((pk, f"title shares no token with part name: {title[:80]!r}"))
        continue

    og = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
                   html, re.I)
    if not og:
        og = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',
                       html, re.I)
    if not og:
        bad.append((pk, f"page verified ({title[:50]!r}) but carries no og:image"))
        continue
    img_url = og.group(1)
    if img_url.startswith("//"):
        img_url = "https:" + img_url

    istatus, idata, ictype = get(img_url, referer=link)
    if istatus is None:
        bad.append((pk, str(idata)))
        continue
    ext = sniff(idata)
    if not ext:
        bad.append((pk, f"og:image gave {ictype}, {len(idata)}B — not an image"))
        continue
    if len(idata) < MIN_IMAGE_BYTES:
        bad.append((pk, f"degenerate image, {len(idata)} bytes"))
        continue

    with open(os.path.join(a.out, f"part_{pk}.{ext}"), "wb") as fh:
        fh.write(idata)
    got.append((pk, ext, len(idata), hashlib.sha256(idata).hexdigest()[:12], title, img_url))
    print(f"ok {pk}: {ext} {len(idata)//1024}KB sha={got[-1][3]}\n"
          f"   page  : {link}\n   title : {title[:90]!r}\n"
          f"   match : {sorted(shared)[:6]}\n   image : {img_url[:110]}")

if got:
    tar = os.path.join(a.out, "images.tar")
    with tarfile.open(tar, "w") as tf:
        for pk, ext, *_ in got:
            n = f"part_{pk}.{ext}"
            tf.add(os.path.join(a.out, n), arcname=n)
    print(f"\ntarball: {tar} ({len(got)} files)")

print(f"\nfetched={len(got)} failed={len(bad)}")
for pk, why in bad:
    print(f"  FAIL {pk}: {why}")
