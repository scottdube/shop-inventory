"""Fetch image bytes ON THE LAPTOP for hosts that refuse the Mini, and tar them
for set_images.py.

Runs locally (`python3 .../scripts/fetch_local.py`), NOT under itq. It exists for
exactly one situation: a vendor CDN that answers this laptop and blocks the
Mini's IP. Measured cases so far — mouser.com/images hands the Mini 13897 bytes
of text/html regardless of Referer (2026-08-29, re-confirmed 2026-08-30), while
m.media-amazon.com serves the Mini real JPEGs happily. So this is a fallback for
named hosts, not the default path; fetching on the Mini is one hop, this is
three.

Output is `part_<pk>.<ext>` files plus a tarball, which is the shape
`scripts/set_images.py --tar` already consumes.

Verifies by CONTENT (magic bytes), never by status code — a defended host
returns 200 with text/html, which is precisely the failure this guards against.
"""
import argparse
import hashlib
import os
import ssl
import tarfile
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

# This laptop's python3 is a portable build whose default trust store points at
# a path from the machine it was BUILT on
# (/Users/runner/work/python-portable-darwin_arm/.../cert.pem), which does not
# exist here. The result is that EVERY https fetch fails with
# CERTIFICATE_VERIFY_FAILED — measured 2026-08-30 against a URL the Mini had
# fetched successfully seconds earlier, which is what proves it is the client
# and not the host. certifi carries a real CA bundle, so use it explicitly.
# Verification stays ON: disabling it to grab a thumbnail would trade a real
# security property for a nice-to-have.
try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # fall back to the default and let the error name itself
    SSL_CTX = None

# pk -> (url, referer, why-this-match-is-provable)
TABLE = {
    108: (
        "https://www.mouser.com/images/alps/images/RKJXT1F42001.jpg",
        "https://www.mouser.com/ProductDetail/688-RKJXT1F42001",
        "og:image filename is the exact MPN RKJXT1F42001, read off the real "
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
ap.add_argument("--out", default="/tmp/laptop_images")
a = ap.parse_args()

os.makedirs(a.out, exist_ok=True)
ok, bad = [], []

for pk, (url, ref, _why) in sorted(TABLE.items()):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": ref,
        "Accept": "image/avif,image/webp,image/jpeg,image/png,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as r:
            data = r.read()
            ctype = r.headers.get("content-type", "?")
    except (urllib.error.URLError, OSError) as e:
        bad.append((pk, f"transport: {e}"))
        continue

    ext = sniff(data)
    if not ext:
        bad.append((pk, f"NOT AN IMAGE — ctype={ctype} bytes={len(data)} "
                        f"first16={data[:16]!r}"))
        continue

    dest = os.path.join(a.out, f"part_{pk}.{ext}")
    with open(dest, "wb") as fh:
        fh.write(data)
    ok.append((pk, dest, len(data), hashlib.sha256(data).hexdigest()[:12]))
    print(f"got {pk}: {ext} {len(data)//1024}KB ctype={ctype} sha={ok[-1][3]}")

if ok:
    tar = os.path.join(a.out, "images.tar")
    with tarfile.open(tar, "w") as tf:
        for _pk, path, _n, _h in ok:
            tf.add(path, arcname=os.path.basename(path))
    print(f"\ntarball: {tar} ({os.path.getsize(tar)//1024}KB, {len(ok)} file(s))")

print(f"\nfetched={len(ok)} failed={len(bad)}")
for pk, why in bad:
    print(f"  FAIL {pk}: {why}")
