"""2026-10-08: staffordspecialtools.com meta-refreshes to
https://www.knurls-sst.com/zencart/ (Zen Cart), reachable from the Mini.
For parts #1337-#1343 print identity, then search the store by SKU and by
name tokens; print candidate product URLs and their image URLs. READ-ONLY.
"""
import gzip, io, os, re, sys, urllib.parse, urllib.request
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
BASE = "https://www.knurls-sst.com/zencart/"


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html',
                                               'Accept-Encoding': 'gzip'})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
        if r.headers.get('Content-Encoding') == 'gzip' or data[:2] == b'\x1f\x8b':
            data = gzip.GzipFile(fileobj=io.BytesIO(data)).read()
        return r.geturl(), data.decode('utf-8', 'replace')


def search(keyword):
    url = BASE + "index.php?main_page=advanced_search_result&keyword=" + urllib.parse.quote(keyword)
    final, txt = fetch(url)
    # product links in Zen Cart search results
    prods = re.findall(r'href="([^"]*main_page=product_info[^"]*products_id=(\d+)[^"]*)"[^>]*>([^<]{3,120})</a>', txt)
    seen, out = set(), []
    for href, pid, title in prods:
        if pid in seen:
            continue
        seen.add(pid)
        out.append((pid, title.strip(), href.replace('&amp;', '&')))
    return out


for p in Part.objects.filter(pk__range=(1337, 1343)).order_by("pk").prefetch_related("supplier_parts"):
    sps = [(sp.SKU, sp.link) for sp in p.supplier_parts.all()]
    print(f"\n### {p.pk} img={'Y' if p.image else '-'} IPN={p.IPN!r} name={p.name!r}\n    desc={p.description[:120]!r}\n    link={p.link!r} sps={sps}")
    terms = [sku for sku, _ in sps if sku] + [p.IPN] if p.IPN else [sku for sku, _ in sps if sku]
    for t in dict.fromkeys(terms):
        try:
            res = search(t)
            print(f"    search {t!r}: {len(res)} products")
            for pid, title, href in res[:5]:
                print(f"      pid={pid} {title!r}")
        except Exception as e:
            print(f"    search {t!r}: {type(e).__name__}: {e}")

# One product page sample to learn the image markup
try:
    res = search("KPS")
    if res:
        pid, title, href = res[0]
        final, txt = fetch(href if href.startswith('http') else BASE + href.lstrip('/'))
        imgs = re.findall(r'<img[^>]+src="([^"]*images/[^"]+)"[^>]*>', txt)
        print(f"\nsample product pid={pid} {title!r}\n  images: {imgs[:8]}")
except Exception as e:
    print(f"sample: {type(e).__name__}: {e}")
