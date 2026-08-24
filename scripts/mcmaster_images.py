"""Fetch McMaster product images, on the laptop, from order-history thumbnails.

Runs LOCALLY (not via itq) because the bytes are fetched here and shipped to the
Mini as one tarball, same as every other image queue.

## Where the URLs come from

NOT from product pages -- the enrich task file forbids scraping those, and you
do not need them. The `/order-history/` sidebar product filter lists every
product ever ordered, and each thumbnail URL embeds the catalogue number:

    https://www.mcmaster.com/mvD/Contents/gfx/ImageCache/
        <first-3-of-SKU>/<SKU>_<guid><ts>@<size>_<ts>.png

So SKU -> image is a join against a page we are explicitly meant to read.

Harvest the map in the logged-in browser with:

    const re = /ImageCache\\/\\d+\\/([0-9A-Za-z]+?)(?:[_\\-p@])/;
    const out = {};
    for (const i of document.querySelectorAll('img')) {
      const s = i.currentSrc || i.src || '';
      if (s.includes('/mvD/Contents/gfx/ImageCache/')) {
        const m = s.match(re);
        if (m) out[m[1].toUpperCase()] = s;
      }
    }

then write `<SKU>\\t<path-after-ImageCache/>` lines into the --urls file.

## Two things measured 2026-08-23

* **Size token:** `@60p`, `@120p` and `@1x` all accept `@400p` (~43 KB, 400 px).
  `@600p` and larger 404. 400p is the ceiling.
* **The image host needs no session.** Plain curl, no cookies, no auth. Only the
  order-history page itself requires the login.

## Why Python and not a shell loop

The obvious `grep | head | cut` pipeline dies here: this sandbox resolves grep,
curl and file but NOT head, cut, awk or ls, so the shell version exits 127 on
every iteration and reports nothing useful. Python needs none of them.

## Known limit

The sidebar product list caps at **100 products**, so SKUs beyond that never
appear and simply will not be in the harvest. Report them; do not silently
treat a short run as complete.
"""
import argparse
import os
import subprocess
import sys

PREFIX = "https://www.mcmaster.com/mvD/Contents/gfx/ImageCache/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

ap = argparse.ArgumentParser()
ap.add_argument("--need", required=True, help="TSV of <pk>\\t<SKU>")
ap.add_argument("--urls", required=True, help="TSV of <SKU>\\t<path-after-ImageCache/>")
ap.add_argument("--out", required=True, help="directory to write part_<pk>.png into")
ap.add_argument("--size", default="400p")
a = ap.parse_args()

sku_to_pk = {}
with open(a.need) as fh:
    for line in fh:
        parts = line.rstrip("\n").split("\t")
        if len(parts) == 2 and parts[0].strip().isdigit():
            sku_to_pk[parts[1].strip().upper()] = parts[0].strip()

os.makedirs(a.out, exist_ok=True)
ok, bad = [], []

with open(a.urls) as fh:
    rows = [l.rstrip("\n").split("\t") for l in fh if l.strip()]

for sku, path in rows:
    pk = sku_to_pk.get(sku.strip().upper())
    if not pk:
        bad.append((sku, "no matching part pk"))
        continue
    dest = os.path.join(a.out, f"part_{pk}.png")
    r = subprocess.run(
        ["curl", "-s", "-o", dest, "-w", "%{http_code}", "-m", "30", "-A", UA,
         PREFIX + path],
        capture_output=True, text=True)
    code = r.stdout.strip()
    magic = b""
    if os.path.exists(dest):
        with open(dest, "rb") as f:
            magic = f.read(8)
    # A 404 still writes an HTML body, so check the magic bytes, not the size.
    if code == "200" and magic.startswith(b"\x89PNG"):
        ok.append((sku, pk, os.path.getsize(dest)))
    else:
        bad.append((sku, f"http={code}"))
        if os.path.exists(dest):
            os.remove(dest)

print(f"downloaded={len(ok)} failed={len(bad)}")
for sku, why in bad:
    print(f"  FAIL {sku}: {why}")

missing = sorted(set(sku_to_pk) - {s.strip().upper() for s, _ in rows})
if missing:
    print(f"\n{len(missing)} SKU(s) needed but absent from the harvest "
          f"(sidebar caps at 100 products):")
    print("  " + " ".join(missing))
