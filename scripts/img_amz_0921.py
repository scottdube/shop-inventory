"""Queue A, 2026-09-21: fetch AND attach Amazon photos in one pass.

Two halves that used to be two scripts. amz_images_0918.py fetched to a tarball
on the Mini and img_attach_0920.py attached from URLs; splitting them meant a
second hop for bytes that were already on the right machine. The 2026-08-24
supersession established the Mini is no longer bot-challenged for /dp/, so the
fetch and the write now happen in the same process on the same host.

Every guard below was paid for once and is carried over unchanged:

  - verify by CONTENT, never by status -- a 200 with text/html is exactly what a
    defended host returns, so the ASIN must appear in the body and the <title>
    must share a token with the part name (a plausible title alone matched the
    WRONG product twice on 2026-09-17);
  - 404 is DELISTING, not a block -- do not count it toward the backoff;
  - three consecutive non-404 content failures = challenge, stop and back off
    (retries make IP reputation worse, not better);
  - hiRes first, then large -- the legacy /images/P/<ASIN> URL is a 43-byte
    placeholder;
  - accept image bytes on MAGIC BYTES and reject anything under 2KB;
  - identical sha256 across two pks is a placeholder being served twice -- drop
    BOTH, empty beats wrong;
  - never overwrite a non-empty image slot;
  - .save() on this install has reported success and written nothing, so every
    write is verified by re-reading the row.

TARGETS are the imageless rows from image_backlog.py that carry an Amazon
SupplierPart whose SKU is a real ASIN. Deliberately NOT included:

  - pks 57, 1055, 1141, 1146, 1200, 1203 -- SKU is an X00xxxxxxx Amazon-internal
    merchant SKU, not an ASIN; /dp/X00... is not a product page.
  - pks 227, 354, 378 -- medical / personal-care / consumer, already marked NOT
    INVENTORY on the row. Titles deliberately not transcribed here.

Usage:  img_amz_0921.py [--commit]
"""
import argparse
import gzip
import hashlib
import os
import re
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

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

# pk -> ASIN, taken verbatim from the part's Amazon SupplierPart SKU.
TARGETS = {
    160:  "B07QD5JRSH",
    180:  "B06ZZ39JHT",
    231:  "B07QMRFFBC",
    262:  "B00GZ6GK7A",
    273:  "B00MBHXWGY",
    286:  "B004HME5JY",
    308:  "B0CGQVJ93X",
    314:  "B074V28ZVS",
    321:  "B07YWC211G",
    331:  "B00CHTLAIS",
    380:  "B00Y95P2JG",
    405:  "B002JEXWK0",
    412:  "B01BWCYYKG",
    446:  "B098LGLBF4",
    458:  "B00E5WJSHK",
    950:  "B017AYH5G0",
    1249: "B0BGRMFKSQ",
    1252: "B00977GM2M",
    1254: "B01L6SMDU4",
}

MAGIC = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png", b"RIFF": "webp", b"GIF8": "gif"}
MIN_IMAGE_BYTES = 2048
STOPWORDS = {
    "the", "and", "for", "with", "kit", "set", "pcs", "pack", "inch", "mm",
    "new", "mini", "module", "board", "digital", "type", "size", "of", "in",
    "amazon", "com", "dp", "www",
}


def sniff(data):
    for m, ext in MAGIC.items():
        if data.startswith(m):
            if ext == "webp" and data[8:12] != b"WEBP":
                continue
            return ext
    return None


def get(url, referer=None, timeout=40):
    hdr = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    }
    if referer:
        hdr["Referer"] = referer
    req = urllib.request.Request(url, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=timeout,
                                    context=ssl.create_default_context()) as r:
            raw, enc = r.read(), (r.headers.get("content-encoding") or "").lower()
            ctype, status = r.headers.get("content-type", "?"), r.status
    except urllib.error.HTTPError as e:
        raw, enc = e.read(), (e.headers.get("content-encoding") or "").lower()
        ctype, status = e.headers.get("content-type", "?"), e.code
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


def tokens(s):
    return {t for t in re.findall(r"[a-z0-9]{3,}", s.lower()) if t not in STOPWORDS}


ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

got, notes = [], []
challenge_streak = 0

for pk, asin in sorted(TARGETS.items()):
    p = Part.objects.filter(pk=pk).first()
    if not p:
        notes.append((pk, asin, "no such part"))
        continue
    if p.image:
        notes.append((pk, asin, f"already has an image ({p.image.name}) -- left alone"))
        continue
    if not p.active:
        notes.append((pk, asin, "active=False (merge receipt / retired) -- not worth a fetch"))
        continue

    url = f"https://www.amazon.com/dp/{asin}"
    status, body, ctype = get(url)

    if status is None:
        notes.append((pk, asin, body.decode("utf8", "replace")[:90]))
        continue
    if status == 404:
        notes.append((pk, asin, f"404 DELISTED ({len(body)}B) -- listing gone, not a block"))
        print(f"xx {pk} {asin}: 404 DELISTED")
        continue

    html = body.decode("utf8", "replace")
    if asin not in html:
        challenge_streak += 1
        notes.append((pk, asin, f"ASIN absent from a {len(body)}B {ctype} body"))
        print(f"!! {pk} {asin}: ASIN not in page ({len(body)}B) -- challenge or wrong "
              f"page (streak {challenge_streak})")
        if challenge_streak >= 3:
            print("STOPPING: 3 consecutive non-404 content failures -- backing off")
            break
        continue

    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    title = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    if not title:
        notes.append((pk, asin, "no <title> -- page did not render"))
        print(f"!! {pk} {asin}: no <title>")
        continue

    shared = tokens(p.name) & tokens(title)
    if not shared:
        notes.append((pk, asin, f"title shares no token with part name: {title[:80]!r}"))
        print(f"!! {pk} {asin}: title/name mismatch -- {title[:70]!r}")
        continue

    challenge_streak = 0

    img_url = None
    for field in ("hiRes", "large"):
        for mm in re.finditer(r'"%s"\s*:\s*"(https://[^"]+)"' % field, html):
            cand = mm.group(1).replace("\\/", "/")
            if "media-amazon.com" in cand or "ssl-images-amazon.com" in cand:
                img_url = cand
                break
        if img_url:
            break
    if not img_url:
        notes.append((pk, asin, "page verified but carries no hiRes/large URL"))
        print(f"!! {pk} {asin}: no hiRes/large URL in page JSON")
        continue

    istatus, idata, ictype = get(img_url, referer=url)
    if istatus is None:
        notes.append((pk, asin, idata.decode("utf8", "replace")[:90]))
        continue
    ext = sniff(idata)
    if not ext:
        notes.append((pk, asin, f"CDN gave {ictype} {len(idata)}B, not an image"))
        print(f"!! {pk} {asin}: CDN returned {ictype}, {len(idata)}B")
        continue
    if len(idata) < MIN_IMAGE_BYTES:
        notes.append((pk, asin, f"degenerate image, {len(idata)}B -- placeholder"))
        print(f"!! {pk} {asin}: {len(idata)}-byte image")
        continue

    got.append({"pk": pk, "asin": asin, "ext": ext, "data": idata,
                "sha": hashlib.sha256(idata).hexdigest(), "title": title,
                "shared": sorted(shared)[:6], "name": p.name})
    print(f"ok {pk} {asin}: {ext} {len(idata)//1024}KB | shared={sorted(shared)[:4]} "
          f"| title={title[:52]!r}")

seen = {}
for g in got:
    seen.setdefault(g["sha"], []).append(g["pk"])
dupes = {s for s, pks in seen.items() if len(pks) > 1}
for s in dupes:
    print(f"\n!! PLACEHOLDER: sha {s[:12]} served for pks {seen[s]} -- identical bytes "
          f"for different products. Dropping ALL; empty beats wrong.")
    notes.append((seen[s][0], "-", f"dropped: shared sha with pks {seen[s]}"))
got = [g for g in got if g["sha"] not in dupes]

ok = failed = 0
if a.commit:
    for g in got:
        p = Part.objects.get(pk=g["pk"])
        p.image.save(f"part_{g['pk']}.{g['ext']}", ContentFile(g["data"]), save=True)
        fresh = Part.objects.get(pk=g["pk"])
        if fresh.image:
            ok += 1
        else:
            print(f"!! {g['pk']}: save reported success but the row is still empty")
            failed += 1

print(f"\nfetched={len(got)} written={ok} failed_verify={failed} "
      f"not_attempted={len(notes)}{'  (DRY RUN)' if not a.commit else ''}")
for pk, asin, why in notes:
    print(f"  - {pk} {asin}: {why}")

allp = Part.objects.count()
allhave = Part.objects.exclude(image="").exclude(image__isnull=True).count()
print(f"coverage: {allhave}/{allp} parts have an image")
