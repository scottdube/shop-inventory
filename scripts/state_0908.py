"""State read for the 2026-09-08 02:05 overnight run. Read-only.

Same shape as state_0907.py: queue A's SupplierPart pool was closed 2026-09-01
and queue B outright on 09-06, so what matters is the DELTA (parts created since
closure, imageless parts on genuinely OPEN POs) plus queue D's remaining
null-safe keyword backlog and queue C's sweep window.

Adds a read of the pending_decisions.md queue and the recorded PO sweep date,
which state_0907.py left to a second round trip.
"""
import os
import re
import sys
from collections import Counter
from datetime import timedelta

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.utils import timezone  # noqa: E402
from company.models import SupplierPart  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402
from part.models import Part  # noqa: E402

ROOT = "/Volumes/4TB_Removable/inventree"
EMPTY_KW = Q(keywords__isnull=True) | Q(keywords="")

active = Part.objects.filter(active=True)
imageless = active.filter(image="")
print(f"active parts            : {active.count()}")
print(f"  imageless (active)    : {imageless.count()}")
print(f"  empty keywords (null-safe, active) : {active.filter(EMPTY_KW).count()}")
print(f"  empty keywords (null-safe, all)    : {Part.objects.filter(EMPTY_KW).count()}")

print()
print("-- queue A reachable-handle buckets among imageless active parts --")
with_sp, with_link, neither = [], [], []
for p in imageless:
    sps = list(SupplierPart.objects.filter(part=p))
    if sps:
        with_sp.append((p, sps))
    elif p.link:
        with_link.append(p)
    else:
        neither.append(p)
print(f"   has SupplierPart : {len(with_sp)}   (pool closed 2026-09-01)")
print(f"   has Part.link    : {len(with_link)}")
print(f"   neither (camera) : {len(neither)}")

print()
print("-- POST-CLOSURE delta: imageless parts WITH a handle created on/after 2026-09-01 --")
CLOSURE = timezone.now().date().replace(month=9, day=1)
found = 0
for p, sps in with_sp:
    if p.creation_date and p.creation_date >= CLOSURE:
        found += 1
        for sp in sps:
            sup = sp.supplier.name if sp.supplier else "?"
            print(f"   pk {p.pk:5d} | {p.name[:44]:<44} | created {p.creation_date} | "
                  f"{sup}:{sp.SKU} | link={sp.link or p.link or '-'}")
for p in with_link:
    if p.creation_date and p.creation_date >= CLOSURE:
        found += 1
        print(f"   pk {p.pk:5d} | {p.name[:44]:<44} | created {p.creation_date} | "
              f"LINK-ONLY {p.link}")
if not found:
    print("   (none)")

print()
print("-- PO status histogram --")
hist = Counter(PurchaseOrder.objects.values_list("status", flat=True))
for code, n in sorted(hist.items()):
    try:
        label = PurchaseOrderStatus(code).label
    except ValueError:
        label = "?"
    print(f"   {code:3d} {label:<12} {n}")

OPEN = [PurchaseOrderStatus.PENDING.value, PurchaseOrderStatus.PLACED.value]

print()
print("-- imageless parts on OPEN purchase orders (queue A jumps these) --")
lines = (PurchaseOrderLineItem.objects
         .filter(order__status__in=OPEN)
         .select_related("order", "part", "part__part", "order__supplier"))
seen, hits = set(), 0
for li in lines:
    sp = li.part
    p = sp.part if sp else None
    if not p or p.pk in seen:
        continue
    seen.add(p.pk)
    if p.image:
        continue
    hits += 1
    print(f"   pk {p.pk:5d} | {p.name[:46]:<46} | "
          f"{li.order.reference} {PurchaseOrderStatus(li.order.status).label:<8} | "
          f"{(li.order.supplier.name if li.order.supplier else '?')}:{sp.SKU}")
print(f"   ({len(seen)} distinct parts on open POs, {hits} imageless)")

print()
print("-- parts created in the last 5 days --")
since = timezone.now() - timedelta(days=5)
for p in Part.objects.filter(creation_date__gte=since.date()).order_by("pk"):
    print(f"   pk {p.pk:5d} | {p.name[:44]:<44} | created {p.creation_date} | "
          f"img={'Y' if p.image else 'n'} kw={'Y' if p.keywords else 'n'} "
          f"link={'Y' if p.link else 'n'} active={p.active}")

print()
print("-- most recent POs (queue C idempotency check) --")
for po in PurchaseOrder.objects.order_by("-pk")[:16]:
    print(f"   {po.reference:<9} {PurchaseOrderStatus(po.status).label:<10} "
          f"{str(po.issue_date or po.creation_date):<12} "
          f"{(po.supplier.name if po.supplier else '?'):<20} "
          f"ref={po.supplier_reference!r}")

print()
print("-- OPEN PO lines with no purchase_price (queue C needs-price) --")
npx = 0
for li in lines:
    if li.purchase_price is None:
        npx += 1
        nm = li.part.part.name[:40] if li.part and li.part.part else "?"
        print(f"   {li.order.reference} | {nm:<40} | qty {li.quantity}")
if not npx:
    print("   (none)")

print()
print("-- recorded PO sweep dates in the progress file --")
prog = os.path.join(ROOT, "enrich_progress.md")
try:
    with open(prog) as fh:
        text = fh.read()
    hits = [ln.strip() for ln in text.splitlines()
            if re.search(r"sweep", ln, re.I) and re.search(r"20\d\d-\d\d-\d\d", ln)]
    for ln in hits[-8:]:
        print(f"   {ln[:150]}")
    if not hits:
        print("   (no sweep line found)")
except OSError as exc:
    print(f"   (progress file unreadable: {exc})")

print()
print("-- pending_decisions.md: open items --")
pend = os.path.join(ROOT, "pending_decisions.md")
try:
    with open(pend) as fh:
        for ln in fh:
            if ln.strip().startswith("- [ ]"):
                print(f"   {ln.rstrip()[:150]}")
except OSError as exc:
    print(f"   (decisions file unreadable: {exc})")
