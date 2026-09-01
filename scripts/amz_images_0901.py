"""Queue A: harvest Amazon product photos for imageless parts, ON THE MINI.

Runs under `itq run`. Writes `part_<pk>.<ext>` plus `images.tar` into --out,
which is the shape `scripts/set_images.py --tar` consumes. Attaches nothing
itself — the guards that must not be duplicated (never overwrite a filled slot,
verify the write by re-reading) live in set_images.py.

## Why the Mini and not the laptop

The task file's laptop-fetch-then-scp dance was written when the Mini was
bot-challenged. Measured 2026-08-24 and again by harvest_amazon_images.py on
08-28: the Mini gets real 1.8-2.1 MB product pages and real JPEGs from
m.media-amazon.com. The laptop path still exists (fetch_local.py) for hosts
that genuinely refuse the Mini — Mouser — but Amazon is not one of them.

## Every check here is a trap already paid for

* **404 is DELISTING, not a block** (TRAPS 2026-08-28). Amazon serves a 2296-byte
  "Dogs of Amazon" page for a listing that is gone, from the same IP that serves
  2 MB product pages seconds later. A 404 therefore must NOT count toward the
  challenge-stop counter, or one dead listing aborts the whole run.
* **Verify by CONTENT, never by status code.** A defended host answers 200 with
  text/html. So: the ASIN must appear in the page, the page must carry a
  `<title>`, and the title must share real tokens with the part name. A page
  that loads is not evidence it is *our* page.
* **The legacy `/images/P/<ASIN>` URL is a 43-byte placeholder.** The real
  photo is the `"hiRes"` field in the page JSON, fallback `"large"`.
* **Sameness across products is the placeholder signature.** Five delisted ASINs
  all rendered the same `01RmK+J4pJL._SS80_.gif` in order history. So every
  fetched image is hashed and any digest appearing under more than one pk is
  dropped from ALL of them — a wrong photo is worse than an empty slot, and
  this is the cheapest test that exists for one.
* **Guard on degenerate, not on unfamiliar** (the Lakeshore lesson). The size
  floor here rejects 1-px axes and sub-2KB files, not "small".

## What is deliberately not attempted

X00-prefixed SKUs (X003YG8RRB, X004T1PV1F, X004Y6G6YL, X001NE1LWJ, X002CFDGIF)
are Amazon *internal* SKUs, not ASINs — the same class as the AliExpress
order-line ids closed on 08-31. Ditto the seller-coined bag SKUs
(JINYONBAG-2x2, Aubeco-3x4). `/dp/<internal sku>` is not a lookup, and the
AliExpress finding is that a bad id does not reliably 404: it can serve a real
page for something else entirely. They are listed in SKIP so the next run does
not rediscover them.
"""
import argparse
import gzip
import hashlib
import io
import json
import os
import re
import ssl
import sys
import tarfile
import urllib.error
import urllib.request
import zlib

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

# pk -> (ASIN, part name as InvenTree holds it)
TARGETS = {
    160: ("B07QD5JRSH", "T12 Soldering Iron Tips, Welding Iron Tips"),
    180: ("B06ZZ39JHT", "Quimat UNO R3 Project Starter Kit"),
    231: ("B07QMRFFBC", "150mm Height Gauge Digital Meter Aperture Caliper"),
    256: ("B079JN626M", "3590S-2-103L 10K Ohm 10-Turn Rotary Precision Potentiometer"),
    262: ("B00GZ6GK7A", "RioRand LCD Module"),
    273: ("B00MBHXWGY", "Mitutoyo 293-340-30 Digital Micrometer"),
    286: ("B004HME5JY", "L.S. Starrett 93 Series T-Handle Tap Wrench"),
    308: ("B0CGQVJ93X", "Zigbee Door Sensors, Smart Contact Sensors"),
    314: ("B074V28ZVS", "Digital Soldering Iron Station"),
    321: ("B07YWC211G", "LinkDm Mini Digital Temperature Humidity Meter"),
    331: ("B00CHTLAIS", "IRF540 N-Channel MOSFET 33A 100V TO-220"),
    380: ("B00Y95P2JG", "Norton Abrasives IB64 India AO Combination Grit Benchstone"),
    405: ("B002JEXWK0", "Tap Magic 30128P ProTap Cutting Fluid"),
    412: ("B01BWCYYKG", "kuman nRF24L01+ 2.4GHz Wireless Transceiver"),
    446: ("B098LGLBF4", "E6B2-CWZ6C Incremental Rotary Encoder"),
    458: ("B00E5WJSHK", "SainSmart Arduino UNO R3 ATmega328P Development Board"),
}

SKIP = {
    57: "X003YG8RRB — Amazon internal SKU, not an ASIN",
    227: "self-described NOT INVENTORY (medical) — rule 3, not transcribed",
    354: "self-described NOT INVENTORY (personal care) — rule 3, not transcribed",
    378: "self-described NOT INVENTORY (consumer item)",
    765: "X004T1PV1F — Amazon internal SKU, not an ASIN",
    849: "JINYONBAG-2x2 — seller-coined SKU, not an ASIN",
    850: "JINYONBAG-2x3 — seller-coined SKU, not an ASIN",
    851: "Aubeco-3x4 — seller-coined SKU, not an ASIN",
    950: "B017AYH5G0 — confirmed delisted 2026-08-31 (2313-byte Page Not Found)",
    1055: "X004Y6G6YL — Amazon internal SKU, not an ASIN",
    1141: "X001NE1LWJ — Amazon internal SKU, not an ASIN",
    1146: "X002CFDGIF — Amazon internal SKU, not an ASIN",
}

MAGIC = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png", b"RIFF": "webp", b"GIF8": "gif"}
MIN_IMAGE_BYTES = 2048
STOPWORDS = {
    "the", "and", "for", "with", "kit", "set", "pcs", "pack", "inch", "mm",
    "new", "mini", "module", "board", "digital", "type", "size", "of", "in",
}


def sniff(data):
    for m, ext in MAGIC.items():
        if data.startswith(m):
            if ext == "webp" and data[8:12] != b"WEBP":
                continue
            return ext
    return None


def get(url, referer=None, timeout=40):
    """Return (status, bytes, content-type). Decompresses whatever Amazon sends."""
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
            raw = r.read()
            enc = (r.headers.get("content-encoding") or "").lower()
            ctype = r.headers.get("content-type", "?")
            status = r.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        enc = (e.headers.get("content-encoding") or "").lower()
        ctype = e.headers.get("content-type", "?")
        status = e.code
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
ap.add_argument("--out", default="/tmp/amz_images_0901")
a = ap.parse_args()

os.makedirs(a.out, exist_ok=True)

for pk, why in sorted(SKIP.items()):
    print(f"-  {pk}: not attempted — {why}")
print()

got, delisted, rejected = [], [], []
challenge_streak = 0

for pk, (asin, pname) in sorted(TARGETS.items()):
    url = f"https://www.amazon.com/dp/{asin}"
    status, body, ctype = get(url)

    if status is None:
        rejected.append((pk, asin, body.decode("utf8", "replace")[:90]))
        continue
    if status == 404:
        delisted.append((pk, asin, f"404 DELISTED ({len(body)} bytes)"))
        print(f"xx {pk} {asin}: 404 DELISTED — listing is gone, not a block")
        continue

    html = body.decode("utf8", "replace")

    # --- verify by CONTENT, three independent ways ------------------------
    if asin not in html:
        challenge_streak += 1
        rejected.append((pk, asin, f"ASIN absent from a {len(body)}-byte "
                                   f"{ctype} body — not our page"))
        print(f"!! {pk} {asin}: ASIN not in page ({len(body)} bytes) — "
              f"challenge or wrong page (streak {challenge_streak})")
        if challenge_streak >= 3:
            print("STOPPING: 3 consecutive non-404 failures — backing off "
                  "rather than grinding reputation down")
            break
        continue

    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    title = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    if not title:
        rejected.append((pk, asin, "no <title> — page did not render"))
        print(f"!! {pk} {asin}: no <title>")
        continue

    shared = tokens(pname) & tokens(title)
    if not shared:
        rejected.append((pk, asin, f"title shares no token with the part name: "
                                   f"{title[:80]!r}"))
        print(f"!! {pk} {asin}: title/name mismatch — {title[:70]!r}")
        continue

    challenge_streak = 0

    # --- the real photo is hiRes, fallback large --------------------------
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
        rejected.append((pk, asin, "no hiRes/large URL in page JSON"))
        print(f"!! {pk} {asin}: page verified but carries no hiRes/large URL")
        continue

    istatus, idata, ictype = get(img_url, referer=url)
    if istatus is None:
        rejected.append((pk, asin, idata.decode("utf8", "replace")[:90]))
        continue
    ext = sniff(idata)
    if not ext:
        rejected.append((pk, asin, f"CDN gave {ictype} {len(idata)}B, not an image"))
        print(f"!! {pk} {asin}: CDN returned {ictype}, {len(idata)} bytes")
        continue
    if len(idata) < MIN_IMAGE_BYTES:
        rejected.append((pk, asin, f"degenerate image, {len(idata)} bytes "
                                   f"(the 43-byte placeholder class)"))
        print(f"!! {pk} {asin}: {len(idata)}-byte image — placeholder")
        continue

    digest = hashlib.sha256(idata).hexdigest()
    got.append({"pk": pk, "asin": asin, "ext": ext, "data": idata,
                "sha": digest, "title": title, "shared": sorted(shared)[:6],
                "url": img_url})
    print(f"ok {pk} {asin}: {ext} {len(idata)//1024}KB sha={digest[:12]} "
          f"| title={title[:60]!r} | matched on {sorted(shared)[:5]}")

# --- sameness across products is the placeholder signature ----------------
seen = {}
for g in got:
    seen.setdefault(g["sha"], []).append(g["pk"])
dupe_shas = {s for s, pks in seen.items() if len(pks) > 1}
if dupe_shas:
    for s in dupe_shas:
        print(f"\n!! PLACEHOLDER: sha {s[:12]} served for pks {seen[s]} — "
              f"identical bytes across different products. Dropping ALL of them; "
              f"an empty slot beats a wrong photo.")
    got = [g for g in got if g["sha"] not in dupe_shas]

for g in got:
    with open(os.path.join(a.out, f"part_{g['pk']}.{g['ext']}"), "wb") as fh:
        fh.write(g["data"])

tar = os.path.join(a.out, "images.tar")
if got:
    with tarfile.open(tar, "w") as tf:
        for g in got:
            n = f"part_{g['pk']}.{g['ext']}"
            tf.add(os.path.join(a.out, n), arcname=n)
    print(f"\ntarball: {tar} ({os.path.getsize(tar)//1024}KB, {len(got)} files)")

with open(os.path.join(a.out, "provenance.json"), "w") as fh:
    json.dump([{k: v for k, v in g.items() if k != "data"} for g in got],
              fh, indent=1)

print(f"\nfetched={len(got)} delisted={len(delisted)} rejected={len(rejected)} "
      f"not_attempted={len(SKIP)}")
for pk, asin, why in delisted + rejected:
    print(f"  - {pk} {asin}: {why}")
