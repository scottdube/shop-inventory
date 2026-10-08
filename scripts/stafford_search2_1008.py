"""2026-10-08 second pass: the store spells SKUs 'KPS 212' (space). Search the
knurls with space/no-suffix forms, fetch every matched product page, and print
its image list so we can tell a per-product photo from a family placeholder.
Also fetch pid=141 (SKP12D holder). READ-ONLY, no InvenTree access.
"""
import gzip, io, re, urllib.parse, urllib.request

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
    prods = re.findall(r'href="([^"]*main_page=product_info[^"]*products_id=(\d+)[^"]*)"[^>]*>([^<]{3,120})</a>', txt)
    seen, out = set(), []
    for href, pid, title in prods:
        if pid in seen:
            continue
        seen.add(pid)
        out.append((pid, title.strip(), href.replace('&amp;', '&')))
    return out


def product(pid):
    final, txt = fetch(BASE + f"index.php?main_page=product_info&products_id={pid}")
    title = re.search(r'<h1[^>]*>(.*?)</h1>', txt, re.S)
    imgs = re.findall(r'<img[^>]+src="([^"]*images/[^"]+)"[^>]*>', txt)
    model = re.search(r'Model:?\s*</?[^>]*>?\s*([A-Z0-9 \-]+)', txt)
    price = re.search(r'\$([0-9]+\.[0-9]{2})', txt)
    desc = re.sub(r'<[^>]+>', ' ', txt)
    desc = re.sub(r'\s+', ' ', desc)
    i = desc.find('Model')
    return (re.sub(r'<[^>]+>', '', title.group(1)).strip() if title else '-',
            [u for u in dict.fromkeys(imgs)], price.group(1) if price else '-', desc[i:i+200] if i >= 0 else '-')


for kw in ("KPS 225", "KPR 225", "KPL 225", "KPS 235", "KPR 235", "KPL 235", "225B", "235B", "25 TPI", "35 TPI"):
    try:
        res = search(kw)
        print(f"search {kw!r}: {len(res)}")
        for pid, title, href in res[:8]:
            print(f"   pid={pid} {title!r}")
    except Exception as e:
        print(f"search {kw!r}: {type(e).__name__}: {e}")

print("\n=== product pages ===")
pids = ["141"]
for kw in ("KPS 225", "KPR 225", "KPL 225", "KPS 235", "KPR 235", "KPL 235"):
    try:
        for pid, title, href in search(kw)[:3]:
            if pid not in pids:
                pids.append(pid)
    except Exception:
        pass
for pid in pids[:14]:
    try:
        t, imgs, price, model = product(pid)
        print(f"pid={pid} title={t!r} price={price}\n   imgs={imgs}\n   {model!r}")
    except Exception as e:
        print(f"pid={pid}: {type(e).__name__}: {e}")
