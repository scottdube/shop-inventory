#!/usr/bin/env python3
"""Overnight 2026-10-23 probe: queue A open-PO pool + queue D empty keywords.

Read-only. Lists every part on a PLACED purchase order that has no image,
with its supplier SKUs and link, plus the high-water mark of part pks and the
count of active parts with empty keywords. Same shape as probe_1022_0205.py,
recent window moved to pk >= 1419 so anything created since the 10-22 runs shows.
Also lists the imageless active parts that carry an Amazon/eBay/AliExpress SKU
or a link, so a run with an empty open-PO pool still has a queue-A target list.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from order.models import PurchaseOrder  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402
from part.models import Part  # noqa: E402

placed = PurchaseOrder.objects.filter(status=PurchaseOrderStatus.PLACED.value)
print(f"placed POs: {placed.count()}")
seen = set()
for po in placed.order_by("-pk")[:40]:
    for line in po.lines.all():
        sp = line.part
        if not sp or sp.part_id in seen:
            continue
        p = sp.part
        seen.add(p.pk)
        if p.image:
            continue
        print(f"NOIMG {po.reference} sref={po.supplier_reference} part={p.pk} "
              f"sku={sp.SKU} supplier={sp.supplier.name} active={p.active} "
              f"link={p.link or '-'} name={p.name[:70]!r}")

hwm = Part.objects.order_by("-pk").first()
print(f"part HWM: {hwm.pk} {hwm.name[:60]!r}")
for p in Part.objects.filter(pk__gte=1419).order_by("pk"):
    print(f"recent {p.pk} img={'Y' if p.image else 'N'} kw={'Y' if p.keywords else 'N'} "
          f"active={p.active} link={p.link or '-'} {p.name[:60]!r}")

act = Part.objects.filter(active=True)
empty_kw = act.filter(keywords__isnull=True) | act.filter(keywords="")
print(f"active empty-keywords: {empty_kw.count()}")
for p in empty_kw.order_by("pk")[:30]:
    print(f"  KW {p.pk} cat={p.category.pathstring if p.category else '-'} "
          f"desc={(p.description or '')[:80]!r} name={p.name[:60]!r}")
have = act.exclude(image="").exclude(image__isnull=True).count()
print(f"coverage: {have}/{act.count()} active parts have an image")

noimg = act.filter(image="") | act.filter(image__isnull=True)
print(f"active imageless: {noimg.count()}")
by_sup = {}
for p in noimg.order_by("pk"):
    sps = list(p.supplier_parts.all())
    key = ",".join(sorted({sp.supplier.name for sp in sps})) or "(no supplier part)"
    by_sup.setdefault(key, []).append(p)
for key, parts in sorted(by_sup.items(), key=lambda kv: -len(kv[1])):
    print(f"  SUP {len(parts):3d}  {key}")
print("imageless with a usable SKU or link (first 40):")
n = 0
for p in noimg.order_by("pk"):
    sps = [(sp.supplier.name, sp.SKU) for sp in p.supplier_parts.all()]
    usable = [s for s in sps if s[0] in ("Amazon", "eBay", "AliExpress", "Seeed", "Pololu",
                                          "Mouser", "DigiKey", "Haas Tooling", "Shars")]
    if not usable and not p.link:
        continue
    n += 1
    if n > 40:
        break
    print(f"  IMG {p.pk} sku={usable[:2]} link={p.link or '-'} {p.name[:55]!r}")
newest = PurchaseOrder.objects.order_by("-pk").first()
print(f"newest PO: {newest.reference} sref={newest.supplier_reference} status={newest.status}")
