"""Fetch product images ON THE MINI and assign them. No laptop round-trip.

Supersedes the fetch-locally-then-tar-then-scp path. As of 2026-08-24 the Mini
is not bot-challenged (see docs/TRAPS.md), so unauthenticated fetching can
happen where the data already lives. The laptop is still required for anything
session-bound — Amazon order pages, McMaster order history, Shop.

Three guards, each one paid for:

  * **Verify by MAGIC BYTES, never by status code.** Mouser's image host returns
    13 KB of text/html with a 200. That nearly wrote HTML into two Part.image
    slots on 2026-08-24; `file(1)` caught it.
  * **Never overwrite a non-empty image.** A vendor stock photo must not eat a
    photo of the actual unit on the bench.
  * **Re-read after saving.** .save() on this install has reported success and
    written nothing.

Input: TSV of `pk<TAB>url`, or --probe to test URLs without touching the DB.
"""
import argparse
import os
import subprocess
import sys
import tempfile

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.core.files.base import ContentFile  # noqa: E402
from part.models import Part                    # noqa: E402

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# Magic bytes -> extension. Anything else is not an image, whatever the headers say.
MAGIC = [(b"\xff\xd8\xff", "jpg"), (b"\x89PNG\r\n\x1a\n", "png"),
         (b"GIF87a", "gif"), (b"GIF89a", "gif"), (b"RIFF", "webp")]

ap = argparse.ArgumentParser()
ap.add_argument("--tsv", help="pk<TAB>url per line")
ap.add_argument("--probe", nargs="*", default=None, help="just test these URLs")
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()


def fetch(url):
    """Return (ext, bytes) or (None, reason). --compressed matters: Amazon sends
    gzip unasked, and an undecoded body looks like a binary blob."""
    tmp = tempfile.mktemp(suffix=".bin")
    r = subprocess.run(
        ["curl", "-sS", "-L", "--compressed", "--max-time", "45", "-A", UA,
         "-o", tmp, "-w", "%{http_code} %{content_type}", url],
        capture_output=True, text=True, errors="replace", timeout=70)
    meta = (r.stdout or "").strip()
    if not os.path.exists(tmp):
        return None, f"no body ({meta})"
    data = open(tmp, "rb").read()
    os.unlink(tmp)
    if not meta.startswith("200"):
        return None, f"http {meta}"
    for sig, ext in MAGIC:
        if data.startswith(sig):
            if len(data) < 1500:
                return None, f"image but only {len(data)}B — refused as a placeholder"
            return ext, data
    head = data[:60].decode("utf-8", "replace").replace("\n", " ")
    return None, f"NOT AN IMAGE despite {meta} — starts {head!r}"


if a.probe is not None:
    for url in a.probe:
        ext, res = fetch(url)
        print(f"{'OK  ' if ext else 'FAIL'} {url[:78]}")
        print(f"      {(str(len(res)) + 'B ' + ext) if ext else res}")
    raise SystemExit

rows = []
for line in open(a.tsv):
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    pk, _, url = line.partition("\t")
    rows.append((int(pk), url.strip()))

ok = skipped = failed = 0
for pk, url in rows:
    p = Part.objects.filter(pk=pk).first()
    if not p:
        print(f"?? {pk}: no such part"); failed += 1; continue
    if p.image:
        print(f"=  {pk}: already has an image — left alone"); skipped += 1; continue

    ext, res = fetch(url)
    if not ext:
        print(f"!! {pk}: {res}"); failed += 1; continue
    if not a.commit:
        print(f"~  {pk}: WOULD set {len(res)//1024}KB .{ext} — {p.name[:46]}"); continue

    p.image.save(f"part_{pk}.{ext}", ContentFile(res), save=True)
    if Part.objects.get(pk=pk).image:
        print(f"+  {pk}: {len(res)//1024}KB .{ext} — {p.name[:46]}"); ok += 1
    else:
        print(f"!! {pk}: save reported success but the row is still empty"); failed += 1

print(f"\nset={ok} skipped_had_image={skipped} failed={failed} "
      f"{'(DRY RUN)' if not a.commit else ''}")
total = Part.objects.count()
have = Part.objects.exclude(image="").exclude(image__isnull=True).count()
print(f"coverage: {have}/{total}")
