"""Queue A, 2026-09-23: two images from single-product vendor pages.

The reachable pool was measured as exhausted on 09-21/09-22 (delisted ASINs,
discontinued Tormach, search-URL-only Lakeshore/PreciseBits, Akamai Mouser).
Tonight's pool re-measure found two rows nothing had tried, both newer than that
closure — the `closures-go-stale-with-inflow` shape:

  1257  Athom US V2 Smart Plug  -- on OPEN PO-0180, so it jumps the queue
  1250  PropWash Dual Concentric Encoder Kit

URLS ARE DECIDED BY HAND IN THE BROWSER, never searched by this script. Each
passes the identifier guard (TRAPS: accept an image only when the page carries
our identifier verbatim):

  - athom.tech/blank-1/us-v2-plug-for-esphome carries PG03V2-US16A-ESP-1/-2/-4
    in its HTML, our SKU being -2. Image = the page's og:image (first gallery
    slot), Wix media id f83f1a_0797...; the bare /media/<id> path is the
    original, the /v1/fill/... transforms are thumbnails.
  - propwashsim.com/store/p/dual-encoder-kit is the SupplierPart's own stored
    link, and its slug IS our SKU. Image = og:image, DSC_4017a.jpg, gallery 1/2.

Also fills the two EMPTY link fields on 1257/sp748 and 1250 with the product
page just verified. Additive only: a non-empty link or image is never touched.

Guards carried from img_amz_0921.py: magic bytes not content-type, 2 KB floor,
distinct sha256 across the batch, never overwrite, re-read after save.

Usage:  img_attach_0923.py [--commit]
"""
import argparse
import hashlib
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
from company.models import SupplierPart          # noqa: E402
from part.models import Part                      # noqa: E402

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

TARGETS = [
    {"pk": 1257, "sp": 748,
     "page": "https://www.athom.tech/blank-1/us-v2-plug-for-esphome",
     "img": "https://static.wixstatic.com/media/f83f1a_079764ee8c9440e88c0d6c14ff852a17~mv2.png"},
    {"pk": 1250, "sp": 744,
     "page": "https://www.propwashsim.com/store/p/dual-encoder-kit",
     "img": "https://images.squarespace-cdn.com/content/v1/5ce9ac10c21cad0001024709/"
            "1571499398533-BJQN2RCZ0LORRO4L3DJC/DSC_4017a.jpg?format=1500w"},
]

MAGIC = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png", b"RIFF": "webp", b"GIF8": "gif"}
MIN_IMAGE_BYTES = 2048


def sniff(data):
    for m, ext in MAGIC.items():
        if data.startswith(m):
            if ext == "webp" and data[8:12] != b"WEBP":
                continue
            return ext
    return None


def get(url, referer):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer": referer,
        "Accept": "image/png,image/jpeg,image/*;q=0.8"})
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

got = []
for t in TARGETS:
    p = Part.objects.filter(pk=t["pk"]).first()
    if not p:
        print(f"?? {t['pk']}: no such part")
        continue
    if p.image:
        print(f"=  {t['pk']}: already has an image ({p.image.name}) -- left alone")
        continue
    status, data, ctype = get(t["img"], t["page"])
    ext = sniff(data) if status else None
    if not ext:
        print(f"!! {t['pk']}: status={status} {ctype} {len(data)}B -- not an image")
        continue
    if len(data) < MIN_IMAGE_BYTES:
        print(f"!! {t['pk']}: {len(data)}B -- degenerate, placeholder")
        continue
    t.update(ext=ext, data=data, sha=hashlib.sha256(data).hexdigest())
    got.append(t)
    print(f"ok {t['pk']}: {ext} {len(data)//1024}KB sha={t['sha'][:12]} | {p.name[:60]}")

shas = [g["sha"] for g in got]
if len(set(shas)) != len(shas):
    print("!! identical bytes across different products -- dropping ALL")
    got = []

written = failed = links = 0
if a.commit:
    for g in got:
        p = Part.objects.get(pk=g["pk"])
        p.image.save(f"part_{g['pk']}.{g['ext']}", ContentFile(g["data"]), save=True)
        if Part.objects.get(pk=g["pk"]).image:
            written += 1
        else:
            print(f"!! {g['pk']}: save reported success but the row is still empty")
            failed += 1

    for t in TARGETS:
        # link__in=["", None] matches '' only: SQL IN never matches NULL, and
        # these rows are NULL. Measured on the first --commit, which filled 0.
        empty = Q(link="") | Q(link__isnull=True)
        n = Part.objects.filter(empty, pk=t["pk"]).update(link=t["page"])
        n += SupplierPart.objects.filter(empty, pk=t["sp"]).update(link=t["page"])
        links += n
    for t in TARGETS:
        p = Part.objects.get(pk=t["pk"])
        sp = SupplierPart.objects.get(pk=t["sp"])
        print(f"   {t['pk']}: part.link={p.link!r}  sp{t['sp']}.link={sp.link!r}")

print(f"\nfetched={len(got)} images_written={written} failed_verify={failed} "
      f"links_filled={links}{'  (DRY RUN)' if not a.commit else ''}")
allp = Part.objects.count()
have = Part.objects.exclude(image="").exclude(image__isnull=True).count()
print(f"coverage: {have}/{allp} parts have an image")
