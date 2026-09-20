"""Tonight's re-measure: queue A pool, queue D eligibility, recent inflow.

The 2026-09-19 census closed queue A down to "AliExpress 4 + eBay 5, everything
else is a camera job or a policy exclusion". That closure was written against
the rows it examined. `closures-go-stale-with-inflow` says it is silent about
rows added since -- and PO-0178 was created after it ran. So re-measure rather
than inherit.

Read-only.
"""
import os
import sys
from collections import defaultdict
from urllib.parse import urlparse

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402

CUTOFF = "2026-09-19"

NOIMG = Q(image="") | Q(image__isnull=True)

active = Part.objects.filter(active=True)
imageless = active.filter(NOIMG).distinct()

print(f"active parts        : {active.count()}")
print(f"all parts           : {Part.objects.count()}")
print(f"imageless (active)  : {imageless.count()}")
print(f"with image (active) : {active.exclude(NOIMG).count()}")

# ---- queue A: who still has a usable handle, and which rows are NEW ----
by_supplier = defaultdict(list)
link_only = []
no_handle = 0

for p in imageless:
    sps = list(p.supplier_parts.all())
    created = str(getattr(p, "creation_date", "") or "")
    if sps:
        for sp in sps:
            sname = sp.supplier.name if sp.supplier else "?"
            by_supplier[sname].append((p.pk, sp.SKU, p.name, created))
        continue
    link = (p.link or "").strip()
    if link:
        link_only.append((p.pk, urlparse(link).netloc, p.name, created))
        continue
    no_handle += 1

print(f"\n=== queue A handles ===")
print(f"no handle at all    : {no_handle}")
print(f"link only           : {len(link_only)}")
print(f"with a SupplierPart : {sum(len(v) for v in by_supplier.values())}")

print("\n-- imageless WITH a SupplierPart, by supplier (NEW = created >= "
      f"{CUTOFF}) --")
for sname, rows in sorted(by_supplier.items(), key=lambda kv: -len(kv[1])):
    print(f"\n  {sname}  ({len(rows)})")
    for pk, sku, pname, created in sorted(rows):
        flag = "NEW " if created[:10] >= CUTOFF else "    "
        print(f"    {flag}{pk}\t{sku[:30]:<30}\t{created[:10]}\t{pname[:52]}")

print("\n-- imageless, link only --")
for pk, host, pname, created in sorted(link_only):
    print(f"    {pk}\t{host[:28]:<28}\t{created[:10]}\t{pname[:52]}")

# ---- inflow since the last census ----
print(f"\n=== parts created on/after {CUTOFF} ===")
recent = Part.objects.filter(creation_date__gte=CUTOFF).order_by("pk")
for p in recent:
    has = "IMG " if (p.image) else "---- "
    skus = ",".join(sp.SKU for sp in p.supplier_parts.all())[:44]
    print(f"  {has}{p.pk}\t{str(p.creation_date)[:10]}\t{p.name[:46]:<46}\t{skus}")
print(f"  ({recent.count()} rows)")

# ---- queue D ----
print("\n=== queue D: active parts with empty keywords ===")
kwless = active.filter(Q(keywords="") | Q(keywords__isnull=True))
print(f"  eligible: {kwless.count()}")
for p in kwless[:40]:
    print(f"    {p.pk}\t{p.name[:60]}")

# ---- open POs (queue A priority rule) ----
print("\n=== POs not yet complete ===")
for po in PurchaseOrder.objects.exclude(status=30).order_by("-pk")[:12]:
    print(f"  {po.reference}\t{po.supplier_reference[:28]:<28}\t"
          f"status={po.status}\t{po.supplier}")
    for line in po.lines.all():
        part = line.part.part if line.part else None
        if part is None:
            print(f"      (no supplier part)")
            continue
        img = "IMG " if part.image else "---- "
        print(f"      {img}{part.pk}\t{part.name[:50]}")
