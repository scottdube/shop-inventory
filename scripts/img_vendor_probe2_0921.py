"""Queue A probe 2, 2026-09-21: find the actual product-image handle per vendor.

Probe 1 established reachability and killed two vendors outright:
  - Mouser returns "Access to this page has been denied" (Akamai) -- 2 rows dead.
  - Lakeshore and PreciseBits both 404 the search URL shapes guessed at.

What probe 1 also showed is that og:image on these carts is the SITE LOGO, not
the product, so og:image is the wrong handle here and taking it would have put
a Lakeshore logo gif on nine tooling parts. This probe therefore goes after the
per-product image directly:

  - Tormach is Magento and its /search?q=<sku> DID answer, so the result page
    should carry media/catalog/product URLs -- extract and show them.
  - Lakeshore and PreciseBits get sitemap.xml, which needs no search syntax and
    gives every product URL in one fetch.

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


print("=== TORMACH: image urls on the search result page for 39044 ===")
st, html = get("https://tormach.com/search?q=39044")
print(f"status={st} bytes={len(html)}")
imgs = sorted(set(re.findall(r'https://[^"\'\\ ]+/media/catalog/product/[^"\'\\ ?]+', html)))
for u in imgs[:12]:
    print("  img:", u[:120])
links = sorted(set(re.findall(r'https://tormach\.com/[a-z0-9\-]+\.html', html)))
for u in links[:12]:
    print("  link:", u[:120])
if not imgs and not links:
    print("  (no product media or .html product links found -- shape is wrong)")

for label, sm in (("LAKESHORE", "https://www.lakeshorecarbide.com/sitemap.xml"),
                  ("PRECISEBITS", "https://www.precisebits.com/sitemap.xml")):
    print(f"\n=== {label}: sitemap ===")
    st, body = get(sm)
    print(f"status={st} bytes={len(body) if body else 0}")
    if not body:
        continue
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body)
    print(f"  locs={len(locs)}")
    for u in locs[:8]:
        print("   ", u[:110])

print("\n=== PRECISEBITS: opencart search shape ===")
st, html = get("https://www.precisebits.com/index.php?route=product/search&search=MN208")
print(f"status={st} bytes={len(html) if html else 0}")
if html:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    print("  title:", re.sub(r"\s+", " ", m.group(1)).strip()[:80] if m else "(none)")
    print("  product links:",
          sorted(set(re.findall(r'href="(https://www\.precisebits\.com/[^"]*product[^"]*)"',
                                html)))[:5])
