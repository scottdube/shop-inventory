"""Queue A probe, 2026-09-21: which non-Amazon vendor sites will answer the Mini?

The Amazon half of tonight's pool collapsed -- 16 of 19 ASINs are genuinely
delisted (confirmed in logged-in Chrome from a second origin), so the remaining
reachable backlog is almost entirely Lakeshore Carbide, Precise Bits, Tormach
and a scatter of single rows. None of those has a KNOWN url shape the way Haas
does, so this measures before building: fetch a candidate URL per vendor, report
status, byte count, <title> and whether an og:image is present.

Reports only. Attaches nothing, writes nothing to InvenTree. Verdict is read
from CONTENT -- a 200 carrying a login wall or a search page with no product is
a failure here even though the status says otherwise.
"""
import gzip
import re
import ssl
import urllib.error
import urllib.request
import zlib

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

# (label, url) -- several shapes per vendor because the shape is the unknown.
PROBES = [
    ("lakeshore/root",    "https://www.lakeshorecarbide.com/"),
    ("lakeshore/search",  "https://www.lakeshorecarbide.com/search.php?search_query=17DRLML14"),
    ("lakeshore/product", "https://www.lakeshorecarbide.com/17drlml14/"),
    ("precisebits/root",  "https://www.precisebits.com/"),
    ("precisebits/srch",  "https://www.precisebits.com/search?q=MN208-1250-019F"),
    ("tormach/root",      "https://tormach.com/"),
    ("tormach/search",    "https://tormach.com/search?q=39044"),
    ("tormach/sku",       "https://tormach.com/products/39044"),
    ("mouser/product",    "https://www.mouser.com/ProductDetail/688-RKJXT1F42001"),
    ("propwash/search",   "https://propwashsim.com/search?q=dual-encoder-kit"),
]


def get(url, timeout=30):
    hdr = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    }
    req = urllib.request.Request(url, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=timeout,
                                    context=ssl.create_default_context()) as r:
            raw, enc = r.read(), (r.headers.get("content-encoding") or "").lower()
            return r.status, raw, enc, r.geturl()
    except urllib.error.HTTPError as e:
        raw, enc = e.read(), (e.headers.get("content-encoding") or "").lower()
        return e.code, raw, enc, url
    except (urllib.error.URLError, OSError) as e:
        return None, f"transport: {e}".encode(), "", url


for label, url in PROBES:
    status, raw, enc, final = get(url)
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
    html = raw.decode("utf8", "replace")

    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    title = re.sub(r"\s+", " ", m.group(1)).strip()[:70] if m else "(no title)"
    og = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
                   html, re.I)
    og2 = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',
                    html, re.I)
    ogv = (og or og2).group(1) if (og or og2) else None

    print(f"{label:20s} {str(status):>5} {len(raw):>8}B og:image={'YES' if ogv else 'no ':3s} "
          f"| {title}")
    if ogv:
        print(f"{'':20s}       -> {ogv[:100]}")
    if final != url:
        print(f"{'':20s}       redirected -> {final[:100]}")
