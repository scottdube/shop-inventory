"""Queue A, 02:05 run 2026-10-04: inflow since #1268.

OPEN PO FIRST -- PO-0201 (Haas 1000523832, raised tonight): #1318-#1324. Image
URL derived from the Haas SKU, the same pattern as #1265 (img_attach_0930.py).

THEN THE BAMBU CATALOGUE -- #1269-#1315, created 2026-10-03 by bambu_import.py
with every supplier-part link pointing at the store HOMEPAGE, so no page named
the product. Instrument: the agent Chrome on us.store.bambulab.com.
  - /products.json is 404 (not a public Shopify catalogue); sitemap_products_1
    lists 1,110 handles.
  - each /products/<handle> carries schema.org ProductGroup JSON-LD whose
    hasVariant[] has name + image per variant. A part was accepted ONLY when its
    variant filter (color code like "(10101)", nozzle size + "Complete Hotend",
    plate series, SKU "AA187") left exactly ONE distinct image.
  - refill and spool variants of a color share one image; a color photo is the
    identity, which is the point.

NOT ATTACHED, with why:
  1276 Gratitude Filament Bundle 2x Black -- no store page carries it.
  1302 Smooth PEI Plate H2D/H2S -- the bambu-smooth-pei-plate page now offers
       only an A1 mini variant; an A1-mini plate photo would be the wrong plate.
  1303 Hotend H2/P2S 0.4 HS -- the page has Standard Flow and High Flow 0.4 HS
       variants with DIFFERENT photos and the part does not say which.
  1316 Hatchbox ABS -- no supplier part, no SKU.

Caveats carried into the run notes:
  1271 X1-Carbon Combo -- the only X1C combo page is refurbished-x1c; the photo
       is the X1C Combo product shot, not of a refurbished unit.
  1312 AMS Flipper ZH076 -- the single-variant page's image file is named
       B-ZH072; the store sells one Flipper. Photo shows identity, not SKU.

Also fills an EMPTY Part.link with the product page (Bambu only). Never
overwrites a link or an image. Same guards as img_attach_1003.py: magic bytes
not content-type, size floor, re-read after save.

Usage:  img_attach_1004.py [--commit]
"""
import argparse
import hashlib
import io
import os
import ssl
import sys
import urllib.error
import urllib.request

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.core.files.base import ContentFile  # noqa: E402
from part.models import Part                      # noqa: E402

try:
    from PIL import Image
except ImportError:
    Image = None

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

HAAS = ("https://www.haastooling.com/content/dam/haas-tooling/ecommerce/products/"
        "{a}/{b}/image/{a}-{b}.jpg/_jcr_content/renditions/original./{a}-{b}.jpg")
BB = "https://store.bblcdn.com/s7/default/"
BS = "https://us.store.bambulab.com/products/"

TARGETS = []
for pk, sku in [(1318, "03-0570"), (1319, "03-0085"), (1320, "03-0392"),
                (1321, "03-0575"), (1322, "03-0086"), (1323, "03-0613"),
                (1324, "03-0611")]:
    a, b = sku.split("-")
    TARGETS.append({"pk": pk, "page": "https://www.haastooling.com/",
                    "imgs": [HAAS.format(a=a, b=b)], "link": None, "ipn": sku})

BAMBU = """
1269|bambu-textured-pei-plate|2050f40e3b8941849f174438d3818242/FAP033.jpg
1270|bambu-hotend-x1c|77c85334102b44e7b8af29251b87db78/0.6mm_50cfb17f-9235-46aa-9d94-6c63aafea0b0.png
1271|refurbished-x1c|ecc1d2ff97b04585af34a614f6f321a8/X1CC-compressed.jpg
1272|petg-cf|9b2c4be00adb4d01a6790d7e89cc6c26/PETG-CF.png
1273|pla-basic-filament|9be8ee6d2e094072ab781d45ae24c2e8/Orange.jpg
1274|glue-stick-for-build-plate|74dd4ec7c2bd475ab1ae72520f7257aa/1_1859cf51-0f06-45e1-8c5b-2d73437fc9a1.png
1275|pla-cmyk-lithophane|9ad222aeacc54256ac91cfea01bf4a71/CMYK.jpg
1277|bambu-hotend-x1c|f93f5575c150426b9fa4001f0a0ccf26/0.4mm_adf566eb-82a5-4405-ba42-6f468a049983.png
1278|liquid-glue-for-build-plate|165c27a803c84271ba164f5ed7477439/1834ea701b187eae9ad52a49fb604e5d.png
1279|pla-cf|b1948cb933824fd394e6071042ff6d00/PLA-CFBlack.jpg
1280|pla-basic-filament|d9f087ffd3ae4283893f8a07d6b7e42a/PLA-Basic_Black_e33768fd-c87a-4b2d-a3f7-0b3afc81f13f.png
1281|pla-matte|9d9735b366524d0e82bf75672a00b7c8/Matte-Mandarin-Orange.png
1282|pla-basic-filament|c93d0a825f094387a61ba3d5ae0499c7/Red.jpg
1283|pla-basic-filament|dd18e1115a7e444396617a3a884aa091/Bambu_Green.jpg
1284|pla-basic-filament|d9f087ffd3ae4283893f8a07d6b7e42a/PLA-Basic_Black_e33768fd-c87a-4b2d-a3f7-0b3afc81f13f.png
1285|pla-basic-filament|5728a39780844f06a9dc4bf3c3907a15/Yellow.jpg
1286|abs-filament|cfdefec225e6430c82cbe2f8766b6f70/ABS_Black.png
1287|support-for-pla-petg|4a9d988773b14e93914f82f888afd771/3_6307a9b6-9d3e-4ab6-be1c-bbeeb8ee6f1c.jpg
1288|bambu-hotend-x1c|9d0c2c5ad2ec4f4297c08b99a1fa62fa/0.2mm_f716cba0-4e66-4184-814b-2d30b0ebaf41.png
1289|bambu-cool-plate-supertack|0bd51861979e49bba57306ccca5da5a2/FAP023-V1.jpg
1290|petg-cf|9b2c4be00adb4d01a6790d7e89cc6c26/PETG-CF.png
1291|pla-basic-filament|dd18e1115a7e444396617a3a884aa091/Bambu_Green.jpg
1292|pla-basic-filament|c93d0a825f094387a61ba3d5ae0499c7/Red.jpg
1293|pla-basic-filament|18de47bcc5d9405596014400afd8a661/PLA_Basic_White.jpg
1294|petg-hf|834a8ad1816747b290e1d6c0ea018942/PETGHF_6.jpg
1295|pla-cf|2bb97e74199a40799302931dc10646cc/c0f99c4f6c04f5422dcd8db2da060392.png
1296|pla-cf|d31d066b74fe46f5a2650df891d25472/83c1bc164a2861ecc083568a0b017ba0_6703fb22-ad79-40f6-b4bf-6053c8d1d9ed.png
1297|abs-filament|1ad485ff4a72413b90e944ffde4fa861/ABS_White.png
1298|pla-basic-filament|e0b16d45e5d64df88f8bca8609f9a0d2/Pink.jpg
1299|pla-basic-filament|d5ba9b091d33481fa397bab61034f031/PumpkinOrange.jpg
1300|tpu-85a-tpu-90a|49e65cb79b5547cfa02b8807aa681f61/TPU_90_BK.png
1301|petg-hf|834a8ad1816747b290e1d6c0ea018942/PETGHF_6.jpg
1304|h2d|e5f6ad2d8168485f82574369073ba155/H2DHT-compressed.jpg
1305|m3-flat-head-cap-machine-screws-fhcs|d539a9d301a74f9bbd9bc1f374f98753/1_20d577e0-a06c-407f-850e-44dadd239557.png
1306|tpu-85a-tpu-90a|ca1edf855bc34e54b96cf61ae8274926/BLACK.jpg
1307|pla-basic-filament|cda8ef4f247943c6934ff1d3a9eef195/HotPink.jpg
1308|pla-wood|4ec4e679110a4bddb7418dd80decc44a/2_1d60446b-f861-4001-9603-2ee01c41de2e.jpg
1309|pla-wood|0b755a3ec3e643c08361f51ec04dbdd9/1_93ade14c-063a-45cb-9c67-1a526d886835.jpg
1310|abs-gf|bc29069d5de746feb4fca56e2871a53a/JP36181.png
1311|pla-basic-beginner-s-filament-pack|eba4fb3d06fd416f99d5f78293ea5b2d/20250811-115747.jpg
1312|ams-flipper-for-p1s-x1-series|61f2ac14cedf4f22a08bbdd16c17d749/B-ZH072_(2).png
1313|pla-basic-filament|5728a39780844f06a9dc4bf3c3907a15/Yellow.jpg
1314|pla-basic-filament|9b179992f52643b2b91c213d86a0c5e1/Magenta.jpg
1315|pla-basic-filament|beb1e91ec6f44fa7a12e0793337d7c52/CMYK-Cyan-1.png
"""
for line in BAMBU.strip().splitlines():
    pk, handle, path = line.split("|")
    TARGETS.append({"pk": int(pk), "page": BS + handle, "imgs": [BB + path],
                    "link": BS + handle, "ipn": None})

MAGIC = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png", b"RIFF": "webp", b"GIF8": "gif"}
MIN_IMAGE_BYTES = 8192


def sniff(data):
    for m, ext in MAGIC.items():
        if data.startswith(m):
            if ext == "webp" and data[8:12] != b"WEBP":
                continue
            return ext
    return None


def dims(data):
    if not Image:
        return "?"
    try:
        w, h = Image.open(io.BytesIO(data)).size
        return f"{w}x{h}"
    except Exception as e:  # noqa: BLE001
        return f"unreadable({e.__class__.__name__})"


def get(url, referer):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer": referer,
        "Accept": "image/png,image/jpeg,image/webp,image/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=40,
                                    context=ssl.create_default_context()) as r:
            return r.status, r.read(), r.headers.get("content-type", "?")
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get("content-type", "?")
    except (urllib.error.URLError, OSError) as e:
        return None, str(e).encode(), "?"


ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

got, links = [], []
for t in TARGETS:
    p = Part.objects.filter(pk=t["pk"]).first()
    if not p:
        print(f"?? {t['pk']}: no such part")
        continue
    if t["ipn"] and p.IPN != t["ipn"]:
        print(f"!! {t['pk']}: IPN {p.IPN!r} != {t['ipn']} -- skipped")
        continue
    if t["link"] and not p.link:
        links.append((t["pk"], t["link"]))
    if p.image:
        print(f"=  {t['pk']}: already has an image ({p.image.name}) -- left alone")
        continue
    for url in t["imgs"]:
        status, data, ctype = get(url, t["page"])
        ext = sniff(data) if status == 200 else None
        if not ext:
            print(f"   miss {t['pk']} status={status} {ctype} {len(data)}B  {url[-60:]}")
            continue
        if len(data) < MIN_IMAGE_BYTES:
            print(f"   miss {t['pk']} {len(data)}B below floor  {url[-60:]}")
            continue
        t.update(ext=ext, data=data, sha=hashlib.sha256(data).hexdigest(), url=url)
        got.append(t)
        print(f"ok {t['pk']}: {ext} {len(data)//1024}KB {dims(data)} "
              f"sha={t['sha'][:12]}  {p.name[:48]}")
        break
    else:
        print(f"!! {t['pk']}: no candidate URL produced an image  ({p.name[:48]})")

written = failed = lwritten = 0
if a.commit:
    for g in got:
        p = Part.objects.get(pk=g["pk"])
        p.image.save(f"part_{g['pk']}.{g['ext']}", ContentFile(g["data"]), save=True)
        fresh = Part.objects.get(pk=g["pk"])
        if fresh.image:
            written += 1
        else:
            print(f"!! {g['pk']}: save reported success but the row is still empty")
            failed += 1
    for pk, link in links:
        # link__in=["", None] matched nothing on the first run: the empty links
        # are NULL, and SQL IN never matches NULL.
        n = (Part.objects.filter(pk=pk)
             .filter(Q(link="") | Q(link__isnull=True)).update(link=link))
        if Part.objects.get(pk=pk).link == link:
            lwritten += 1
        else:
            print(f"!! {pk}: link did not stick (update n={n})")

print(f"\ntargets={len(TARGETS)} fetched={len(got)} images_written={written} "
      f"failed_verify={failed} links_filled={lwritten}/{len(links)}"
      f"{'  (DRY RUN)' if not a.commit else ''}")
act = Part.objects.filter(active=True)
have = act.exclude(image="").exclude(image__isnull=True).count()
print(f"coverage: {have}/{act.count()} active parts have an image")
