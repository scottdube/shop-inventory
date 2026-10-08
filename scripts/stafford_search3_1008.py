"""2026-10-08 third pass. (1) What did the Stafford PO lines actually say
(order title, qty, price) for parts #1337-#1343? (2) Walk the store's product
listing for every 'KP' model so the 35 TPI knurls and any 'B' suffix show up.
(3) Dump pid 525's description text for a bevel note. READ-ONLY.
"""
import gzip, io, os, re, sys, urllib.parse, urllib.request
import django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part
from order.models import PurchaseOrderLineItem

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


print("=== PO lines for 1337-1343 ===")
for line in PurchaseOrderLineItem.objects.filter(part__part__pk__range=(1337, 1343)).select_related("order", "part"):
    print(f"{line.order.reference} sref={line.order.supplier_reference!r} part={line.part.part.pk} sku={line.part.SKU!r} "
          f"qty={line.quantity} price={line.purchase_price} ref={line.reference!r} notes={line.notes!r}")
    print(f"    po.notes={line.order.notes[:300]!r}" if line.order.notes else "    po.notes=''")

print("\n=== store: all products whose title has 'KP' (search 'Knurls') ===")
models = {}
for kw in ("Knurls", "Circular Pitch", "KPS", "KPR", "KPL", "KP"):
    for page in range(1, 8):
        url = BASE + "index.php?main_page=advanced_search_result&keyword=" + urllib.parse.quote(kw) + f"&page={page}"
        try:
            final, txt = fetch(url)
        except Exception as e:
            print(f"{kw} p{page}: {type(e).__name__}: {e}")
            break
        prods = re.findall(r'href="([^"]*main_page=product_info[^"]*products_id=(\d+)[^"]*)"[^>]*>([^<]{3,120})</a>', txt)
        new = 0
        for href, pid, title in prods:
            if pid not in models:
                models[pid] = title.strip()
                new += 1
        if not prods or new == 0:
            break
print(f"{len(models)} distinct products seen")
for pid, title in sorted(models.items(), key=lambda kv: kv[1]):
    if re.search(r'\bKP[SRL]', title):
        print(f"  pid={pid} {title}")

print("\n=== pid 525 text ===")
final, txt = fetch(BASE + "index.php?main_page=product_info&products_id=525")
body = re.sub(r'<script.*?</script>', ' ', txt, flags=re.S)
body = re.sub(r'<[^>]+>', ' ', body)
body = re.sub(r'\s+', ' ', body)
i = body.find('Circular Pitch Knurls Tool#')
print(body[i:i+1500])

print("\n=== pid 141 text ===")
final, txt = fetch(BASE + "index.php?main_page=product_info&products_id=141")
body = re.sub(r'<script.*?</script>', ' ', txt, flags=re.S)
body = re.sub(r'<[^>]+>', ' ', body)
body = re.sub(r'\s+', ' ', body)
i = body.find('Adjustable Straddle Holders HD')
print(body[i:i+1200])
