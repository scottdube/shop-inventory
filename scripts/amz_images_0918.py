"""Queue A, 2026-09-18: fetch Amazon photos for 12 parts recovered by
order-history search. Runs on the Mini under `itq run`; attaches nothing.

Same machinery as amz_images_0901.py — every guard in that file's docstring is
load-bearing and is repeated here unchanged (404 is delisting not a block;
verify by CONTENT not status; hiRes then large; drop any digest that appears
under more than one pk; reject degenerate sub-2KB files).

WHERE THESE ASINs CAME FROM, because it is not a stored handle. None of these 12
parts has a SupplierPart or a Part.link — they are in the bucket the state probe
calls "no handle". What they DO carry is a prose provenance line in the
description ("pack: 32; via Amazon; last ordered 2026-03-15"), and
amazon.com/your-orders/search?search=<token> resolves that to a real order card
with a /dp/<ASIN> anchor on it.

Each ASIN below was confirmed on the ORDER DATE equalling the recorded
last-ordered date, plus the listing title, and for seven of them a third token
(the pack count appearing verbatim in the title: "32 Pcs" = pack 32, "10Pcs" =
pack 10, "2PCS" = pack 2, "5Pcs" = pack 5, "3PCS" = pack 3). The date is the
evidence that matters: the search is token-OR and a plausible title alone
matched the WRONG product twice on 2026-09-17.

TWO REFINEMENTS measured tonight, both worth more than the images:

1. The search endpoint answers a SAME-ORIGIN fetch() from an already-open
   amazon.com tab with the full server-rendered result page (~400KB). So a whole
   night's worth of candidates can be searched in one tool call instead of one
   navigation each. `/your-orders/orders` does NOT: it comes back as a blocked
   cookie shell with zero /dp/ anchors, so paging the year list — the "obvious
   next lever" the 09-17 run named — is closed by fetch and would need real
   navigations.

2. A query that matches nothing does not say so. It returns the generic
   recency-ordered order list, which LOOKS like a result set: every multi-word
   query tonight returned the same Waveshare/Chip-Quik/PATIKIL head. Only the
   date filter distinguishes a hit from that default. "No results found" (the
   2026-09-16 calibration) is reachable, but a noise query does not reach it.

STILL UNRECOVERED, reason named rather than called dead: pk 43 (uxcell 2.54mm
Female 30-Pin Flat Cable IDC, recorded 2025-01-06). Five tokens tried — "IDC",
"ribbon", "flat cable", "socket", "uxcell 2.54mm" — each returned the default
list with nothing dated January 6, 2025. That is a CAPPED read, not an absence:
page one only, and the year-list route that would settle it is the one blocked
in (1) above.
"""
import argparse
import gzip
import hashlib
import json
import os
import re
import ssl
import tarfile
import urllib.error
import urllib.request
import zlib

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

# pk -> (ASIN, part name, order date that confirmed it)
TARGETS = {
    2:  ("B07QGSW4Q1", "uxcell SMD Chip Resistor 220 Ohm 1/4W 1206", "2026-07-09"),
    9:  ("B07XQ1Q9RN", "RK097N Linear Potentiometer 10K", "2023-10-31"),
    10: ("B0G55X8DDG", "10K Ohm Linear Taper Dimmer Potentiometer", "2026-02-12"),
    21: ("B07K7JF3HX", "CD74HC4067 16-Channel Analog Multiplexer", "2024-01-07"),
    29: ("B07P2BLG2L", "ALEDECO PWM DC Motor Speed Controller", "2023-10-30"),
    30: ("B0C17NLZNH", "DC Power Supply Variable 30V 10A Bench", "2023-09-03"),
    63: ("B09J95SMG7", "Teyleten Robot ESP32S ESP-WROOM-32 Dev Board", "2024-05-04"),
    64: ("B0DJ6N55FX", "XIAO ESP32C6 Pack WiFi6 BLE5 Zigbee Matter", "2026-05-25"),
    68: ("B0DXF39GPM", "ESP32-S3 2.8inch Round Display Dev Board", "2025-07-17"),
    79: ("B09Y8ZG4K1", "Shelly Plus 2PM WiFi BT 2ch Smart Relay", "2024-04-01"),
    81: ("B072Z7Y19F", "ELEGOO Double Sided PCB Prototype Board", "2026-03-15"),
    91: ("B0G2QW33X1", "ATTEN ST-862D 1000W Hot Air Rework Station", "2026-06-18"),
}

# pk 63's order of 2024-05-04 carried TWO ESP-WROOM-32 listings: B08D5ZD528
# (unbranded) and B09J95SMG7 (Teyleten Robot). The part's own name says Teyleten
# Robot, so that is the one taken. Recorded here because the other ASIN is a real
# board on a real order with no part behind it, which is a question, not a bug.

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
ap.add_argument("--out", default="/tmp/amz_images_0918")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

got, delisted, rejected = [], [], []
challenge_streak = 0

for pk, (asin, pname, when) in sorted(TARGETS.items()):
    url = f"https://www.amazon.com/dp/{asin}"
    status, body, ctype = get(url)

    if status is None:
        rejected.append((pk, asin, body.decode("utf8", "replace")[:90]))
        continue
    if status == 404:
        delisted.append((pk, asin, f"404 DELISTED ({len(body)} bytes)"))
        print(f"xx {pk} {asin}: 404 DELISTED — listing gone, not a block")
        continue

    html = body.decode("utf8", "replace")

    if asin not in html:
        challenge_streak += 1
        rejected.append((pk, asin, f"ASIN absent from a {len(body)}-byte {ctype} body"))
        print(f"!! {pk} {asin}: ASIN not in page ({len(body)} bytes) — "
              f"challenge or wrong page (streak {challenge_streak})")
        if challenge_streak >= 3:
            print("STOPPING: 3 consecutive non-404 failures — backing off")
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
        rejected.append((pk, asin, f"title shares no token with part name: {title[:80]!r}"))
        print(f"!! {pk} {asin}: title/name mismatch — {title[:70]!r}")
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
        rejected.append((pk, asin, f"degenerate image, {len(idata)} bytes"))
        print(f"!! {pk} {asin}: {len(idata)}-byte image — placeholder")
        continue

    digest = hashlib.sha256(idata).hexdigest()
    got.append({"pk": pk, "asin": asin, "ext": ext, "data": idata, "sha": digest,
                "title": title, "confirmed_on": when, "shared": sorted(shared)[:6],
                "url": img_url})
    print(f"ok {pk} {asin}: {ext} {len(idata)//1024}KB sha={digest[:12]} "
          f"| order {when} | title={title[:58]!r}")

seen = {}
for g in got:
    seen.setdefault(g["sha"], []).append(g["pk"])
dupe_shas = {s for s, pks in seen.items() if len(pks) > 1}
for s in dupe_shas:
    print(f"\n!! PLACEHOLDER: sha {s[:12]} served for pks {seen[s]} — identical "
          f"bytes across different products. Dropping ALL; empty beats wrong.")
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
    json.dump([{k: v for k, v in g.items() if k != "data"} for g in got], fh, indent=1)

print(f"\nfetched={len(got)} delisted={len(delisted)} rejected={len(rejected)}")
for pk, asin, why in delisted + rejected:
    print(f"  - {pk} {asin}: {why}")
