"""Is the Mini actually un-challenged by Amazon, or just returning 200?

docs/TRAPS.md says the LRD network is bot-challenged and the laptop is not, so
image bytes must be fetched on the laptop and scp'd over. A plain curl from the
Mini now returns 200 with 361 KB of text/html -- but a 200 with text/html is
exactly what Mouser's defended image host returns, so status code proves
nothing. Test the CONTENT.
"""
import re
import subprocess

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
ASIN = "B09YHWKKTR"   # PATIKIL FR4 copper clad, part #1082

html = subprocess.run(
    ["curl", "-sS", "-L", "--compressed", "--max-time", "40", "-A", UA,
     f"https://www.amazon.com/dp/{ASIN}"],
    capture_output=True, text=True, errors="replace", timeout=60).stdout

title = re.search(r"<title>([^<]*)", html)
hi = re.search(r'"hiRes":"(https:[^"]+)"', html)
print(f"bytes            : {len(html)}")
print(f"title            : {(title.group(1).strip()[:80] if title else '(none)')}")
print(f"challenge words  : {bool(re.search(r'not a robot|Enter the characters|automated access|Sorry, we just need', html, re.I))}")
print(f'"hiRes" present  : {bool(hi)}')
if hi:
    url = hi.group(1).replace("\\u002F", "/")
    print(f"hiRes url        : {url[:96]}")
    out = subprocess.run(
        ["curl", "-sS", "-o", "/tmp/mini_test.jpg", "-L", "--max-time", "40", "-A", UA,
         "-w", "%{http_code} %{size_download} %{content_type}", url],
        capture_output=True, text=True, errors="replace", timeout=60).stdout.strip()
    print(f"CDN fetch        : {out}")
    print(f"file type        : {subprocess.run(['file','-b','/tmp/mini_test.jpg'],capture_output=True,text=True).stdout.strip()[:70]}")
