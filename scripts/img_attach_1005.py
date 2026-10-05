"""Queue A, 02:05 run 2026-10-05: inflow since #1324.

OPEN PO FIRST -- the only imageless open-PO parts besides #1190 (Cults3D STL,
closed long ago):
  1325 PO-0202 eBay 188532551761 Radio Shack strobe -- the listing's own lead
       photo, i.e. the actual unit bought, not a stock shot. Read from the
       carousel in the agent Chrome; s-l1600 .jpg first, .webp and the og:image
       s-l400 as fallbacks.
  1327 PO-0203 DigiKey PB2031-ND (ORWH-SH-124D1F,000) -- og:image of the DigiKey
       product page, the ORWH/OEG SERIES photo (DigiKey shows one per series).
  1328 PO-0203 DigiKey 13-MFP-25BRD52-47KCT-ND -- og:image, the 47k MFP photo.
DigiKey pages are fingerprint-defended, so the URLs came from Chrome; the
mm.digikey.com CDN is fetched here.

NOT ATTACHED, with why:
  1326 Thermal Master P2 Pro -- no supplier part, no SKU; iOS and Android
       variants exist and the part does not cite a listing.
  1329/1330/1331 Saunders Mod Vise GEN2 soft jaws / system / reversible insert
       -- saundersmachineworks.com now sells only Gen3 soft jaws and the Gen3
       vise; the reversible insert has no page at all. A Gen3 photo would be the
       wrong part (same rule as #1302's A1-mini plate).
  1332 Zoro G2455207 angle plate -- zoro.com answered the agent Chrome with a
       DataDome captcha interstitial (geo.captcha-delivery.com). Not solved, by
       rule.

Also fills an EMPTY Part.link with the product/listing page. Never overwrites a
link or an image. Same guards as img_attach_1004.py.

Usage:  img_attach_1005.py [--commit]
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

EB = "https://i.ebayimg.com/images/g/-kQAAeSwI4tqNRF0/"
DK = "https://mm.digikey.com/Volume0/opasdata/d220001/medias/images/"

TARGETS = [
    {"pk": 1325, "ipn": "188532551761",
     "page": "https://www.ebay.com/itm/188532551761",
     "link": "https://www.ebay.com/itm/188532551761",
     "imgs": [EB + "s-l1600.jpg", EB + "s-l1600.webp", EB + "s-l400.jpg"]},
    {"pk": 1327, "ipn": "ORWH-SH-124D1F",
     "page": "https://www.digikey.com/",
     "link": "https://www.digikey.com/en/products/detail/te-connectivity-potter-brumfield-relays/ORWH-SH-124D1F-000/5405938",
     "imgs": [DK + "2138/ORWH%2COEG-Series.JPG"]},
    {"pk": 1328, "ipn": "MFP-25BRD52-47K",
     "page": "https://www.digikey.com/",
     "link": "https://www.digikey.com/en/products/detail/yageo/MFP-25BRD52-47K/2058822",
     "imgs": [DK + "2521/47k-Ohm-Axial-0%2C1%25-MFP.jpg"]},
]

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
