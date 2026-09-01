"""Control test: is the Mini's 16/16 Amazon 404 real delisting, or the instrument?

Written 2026-09-01, immediately after amz_images_0901.py returned 404 on
sixteen of sixteen ASINs, every body exactly 2296 bytes.

The task file's standing rule is that a 404 from Amazon means the listing is
GONE, not that we are blocked — measured 2026-08-28, when 17 of 20 404'd while
3 served 2 MB pages *from the same IP in the same run*. That mixed result is
what made the conclusion safe. A UNIFORM result is a different animal: sixteen
unrelated listings, including a Mitutoyo micrometer and a SainSmart UNO R3 that
have been sold continuously for a decade, do not all vanish at once.

So this runs the one test that can tell the two apart: a **known-live control**
alongside the failures, in the same process, seconds apart.

  * control 404s too  -> the Mini is being served a blanket 404. NOT delisting.
    The 2296-byte body is then a *fingerprinting response wearing a 404*, and
    the standing "404 = gone" rule needs a caveat, because a blanket 404 is
    indistinguishable from delisting on any single fetch.
  * control succeeds   -> the sixteen really are gone, and the run should say so
    with evidence rather than guessing.

B08NTK8JXZ is the control the 2026-08-31 run used to bracket its own sweep, so
it is a live listing of record for this project rather than one picked tonight.
"""
import gzip
import ssl
import urllib.error
import urllib.request
import zlib

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

CASES = [
    ("B08NTK8JXZ", "CONTROL — known live, used to bracket the 08-31 sweep"),
    ("B00E5WJSHK", "SainSmart UNO R3 — pk 458, 404'd tonight"),
    ("B00MBHXWGY", "Mitutoyo 293-340-30 — pk 273, 404'd tonight"),
    ("B0CGQVJ93X", "Zigbee door sensor — pk 308, 404'd tonight, recent listing"),
]

FORMS = [
    "https://www.amazon.com/dp/{a}",
    "https://www.amazon.com/gp/product/{a}",
    "https://www.amazon.com/dp/{a}/ref=nosim",
]


def get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    })
    try:
        with urllib.request.urlopen(req, timeout=40,
                                    context=ssl.create_default_context()) as r:
            raw, enc, status = r.read(), r.headers.get("content-encoding", ""), r.status
            ctype = r.headers.get("content-type", "?")
    except urllib.error.HTTPError as e:
        raw, enc, status = e.read(), e.headers.get("content-encoding", ""), e.code
        ctype = e.headers.get("content-type", "?")
    except (urllib.error.URLError, OSError) as e:
        return None, f"transport: {e}", "?", ""
    if (enc or "").lower() == "gzip":
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
    elif (enc or "").lower() == "deflate":
        try:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        except zlib.error:
            pass
    return status, raw, ctype, raw[:400].decode("utf8", "replace")


for asin, label in CASES:
    print(f"\n=== {asin}  {label}")
    for form in FORMS:
        url = form.format(a=asin)
        status, raw, ctype, head = get(url)
        if status is None:
            print(f"  {url}\n    TRANSPORT FAIL: {raw}")
            continue
        n = len(raw)
        marker = ""
        low = raw.decode("utf8", "replace").lower()
        if "dogs of amazon" in low or "we're sorry" in low:
            marker += " [dogs-of-amazon]"
        if "captcha" in low or "type the characters" in low:
            marker += " [CAPTCHA]"
        if "automated access" in low or "not a robot" in low:
            marker += " [BOT WORDING]"
        if asin.lower() in low:
            marker += " [asin present]"
        print(f"  {url}\n    status={status} bytes={n} ctype={ctype}{marker}")
        print(f"    head: {head[:160]!r}")
