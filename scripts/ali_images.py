"""Assign Part.image from AliExpress order-detail thumbnails, fetched ON THE MINI.

Queue A wrote AliExpress off on 2026-08-23: "SupplierPart.SKU is an order-line
string ('8211821285085753/0.1UF 10mm, 275V AC'), not a product ID — nothing to
look up." That was the wrong conclusion from the right observation. The leading
16 digits ARE the AliExpress order id, and the order-detail page
`/p/order/detail.html?orderId=<id>` shows the exact item purchased, with its
photo. So the SKU was never useless — it was a key into order history.

Two things make this script deliberately different from `set_images.py`:

  * **It downloads on the Mini, not the laptop.** The ae-pic CDN is undefended
    and answers plain urllib. Fetching here removes a laptop curl and an scp
    from the loop — and on 2026-08-27 it was exactly that laptop `cd && curl`
    one-liner, unapprovable by construction, that stalled the overnight run for
    280 minutes. Fewer command shapes is the whole point of `itq`.
  * **It converts to JPEG.** The CDN content-negotiates and serves WebP from a
    `.jpg` URL, so what lands on disk does not match its own extension.

HARVEST NOTE, so nobody re-derives it: the thumbnail is a CSS
`background-image` on `.order-detail-item-content-img`, NOT an `<img>` — a
document-wide `img` scrape returns 140+ "More to love" recommendations instead,
which is the LCSC wrong-part trap in a new costume. Strip the trailing
`_220x220.jpg` size suffix for the full-size original (~1000px).

REJECTED, with the reason, so a later run does not "fix" it:
orders 100837932055753, 91301677995753 and 90294522855753 (parts 727/728/729)
all return the SAME image hash `Sf5a31ce867174aa7bf499352d6875ddc` for three
completely different products. That is a missing-image PLACEHOLDER for
delistings, not a photo, and it arrives in the path form `/kf/<hash>/160x160.png`
rather than the suffix form. Both signals are checked below and both reject.
An empty slot beats a wrong photo (task file rule, wrong-family-photo).
"""
import argparse
import io
import os
import sys
import urllib.request

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.core.files.base import ContentFile  # noqa: E402
from PIL import Image                           # noqa: E402
from part.models import Part                    # noqa: E402

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
MIN_PX = 300  # anything smaller is a thumbnail or a placeholder, not a photo

ap = argparse.ArgumentParser()
ap.add_argument("--tsv", required=True, help="pk<TAB>url per line")
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

rows = []
for line in open(a.tsv):
    line = line.rstrip("\n")
    if not line or line.startswith("#"):
        continue
    pk, _, url = line.partition("\t")
    if url.strip():
        rows.append((int(pk), url.strip()))

# A hash reused across products is a placeholder, never a photo. Catch it here
# as well as by eye, because the eye is not present at 02:00.
seen = {}
for pk, url in rows:
    seen.setdefault(url, []).append(pk)

set_ok = skipped_filled = missing = rejected = failed = 0
for pk, url in rows:
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"?? {pk}: no such part")
        missing += 1
        continue
    if p.image:
        print(f"=  {pk}: already has an image ({p.image.name}) — left alone")
        skipped_filled += 1
        continue

    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        raw = urllib.request.urlopen(req, timeout=30).read()
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as exc:                      # noqa: BLE001 - report, don't crash the batch
        print(f"!! {pk}: fetch/decode failed ({exc}) — {url}")
        rejected += 1
        continue

    w, h = img.size
    if min(w, h) < MIN_PX:
        print(f"XX {pk}: {w}x{h} is below {MIN_PX}px — placeholder or thumbnail, rejected")
        rejected += 1
        continue

    if not a.commit:
        print(f"~  {pk}: WOULD set {w}x{h} {img.format} {len(raw)//1024}KB — {p.name[:48]}")
        continue

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    data = buf.getvalue()
    name = f"part_{pk}_ali.jpg"
    p.image.save(name, ContentFile(data), save=True)

    # Re-read rather than trust the save (docs/TRAPS.md: silent no-op saves).
    fresh = Part.objects.get(pk=pk)
    if fresh.image:
        print(f"+  {pk}: {fresh.image.name} {w}x{h} ({len(data)//1024}KB) — {p.name[:48]}")
        set_ok += 1
    else:
        print(f"!! {pk}: save reported success but the row is still empty")
        failed += 1

print(f"\nset={set_ok} skipped_already_had_image={skipped_filled} missing_part={missing} "
      f"rejected={rejected} failed_verify={failed} {'(DRY RUN)' if not a.commit else ''}")

total = Part.objects.count()
have = Part.objects.exclude(image="").exclude(image__isnull=True).count()
print(f"coverage now: {have}/{total}")
