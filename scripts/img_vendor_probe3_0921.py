"""Queue A probe 3, 2026-09-21: nail the exact image handle for the three
vendors that survived probe 2.

Settled so far: Mouser is Akamai-denied (2 rows dead), og:image on these carts
is the site logo and must not be used, PreciseBits answers the OpenCart search
shape, and Lakeshore/PreciseBits both publish a sitemap. Tormach's search page
returns 200 and says "Search results for '39044'" but carries no product link
matching the .html shape -- so the shape, not the access, is what is wrong, and
this prints the raw neighbourhood of the SKU rather than guessing again.

Reports only. Nothing is written.
"""
import gzip
import re
import ssl
import urllib.error
import urllib.request
import zlib

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

LAKESHORE_SKUS = ["4L-SPTRMLB", "17DRLML14", "17DRLML18", "10-SPTRMLB",
                  "LC206-001313", "1/4-SPTRMLB", "11DRLML14", "13DRLML12",
                  "LC206038"]


def get(url, timeout=40):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml,*/*",
        "Accept-Encoding": "gzip, deflate",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout,
                                    context=ssl.create_default_context()) as r:
            raw, enc, st = r.read(), (r.headers.get("content-encoding") or "").lower(), r.status
    except urllib.error.HTTPError as e:
        raw, enc, st = e.read(), (e.headers.get("content-encoding") or "").lower(), e.code
    except (urllib.error.URLError, OSError) as e:
        return None, f"transport: {e}"
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
    return st, raw.decode("utf8", "replace")


print("=== TORMACH: what is actually around '39044' on the search page ===")
st, html = get("https://tormach.com/search?q=39044")
if html:
    for m in list(re.finditer(r"39044", html))[:3]:
        s = max(0, m.start() - 260)
        print("  ...", re.sub(r"\s+", " ", html[s:m.end() + 260])[:520], "...")
        print("  ---")
    srcs = sorted(set(re.findall(r'(?:src|data-src|content)="(https?://[^"]+\.(?:jpg|jpeg|png|webp))"',
                                 html, re.I)))
    print(f"  image urls on page: {len(srcs)}")
    for u in srcs[:10]:
        print("   ", u[:115])

print("\n=== LAKESHORE: are the SKUs in the sitemap? ===")
st, sm = get("https://www.lakeshorecarbide.com/sitemap.xml")
locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sm or "")
print(f"  sitemap locs={len(locs)}")
for sku in LAKESHORE_SKUS:
    tok = sku.lower().replace("/", "").replace("-", "")
    hit = [u for u in locs if tok in u.lower().replace("-", "")]
    print(f"  {sku:14s} -> {hit[0] if hit else '(not in sitemap)'}")

print("\n=== LAKESHORE: does a category page carry SKU + image together? ===")
st, cat = get("https://www.lakeshorecarbide.com/chamferdrillmills.aspx")
print(f"  status={st} bytes={len(cat) if cat else 0}")
if cat:
    for sku in ("17DRLML14", "11DRLML14"):
        i = cat.find(sku)
        print(f"  {sku}: {'FOUND at %d' % i if i >= 0 else 'absent'}")
        if i >= 0:
            print("    ...", re.sub(r"\s+", " ", cat[max(0, i - 300):i + 200])[:480], "...")

print("\n=== PRECISEBITS: image urls on a product page ===")
st, pp = get("https://www.precisebits.com/index.php?route=product/product&product_id=3340")
print(f"  status={st} bytes={len(pp) if pp else 0}")
if pp:
    m = re.search(r"<title[^>]*>(.*?)</title>", pp, re.S | re.I)
    print("  title:", re.sub(r"\s+", " ", m.group(1)).strip()[:80] if m else "(none)")
    srcs = sorted(set(re.findall(r'https://www\.precisebits\.com/image/[^"\'\s]+', pp)))
    for u in srcs[:8]:
        print("   ", u[:115])
