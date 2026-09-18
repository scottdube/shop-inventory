"""State read for the 2026-09-18 02:05 overnight run. Read-only.

Narrower than state_0912.py on purpose. The 2026-09-17 run established where the
remaining queue A work actually is: NOT in SupplierPart SKUs (that pool closed
2026-09-01) and NOT in Part.link, but in the PROSE provenance line some
descriptions carry -- "pack: 200; via Amazon; last ordered 2026-07-09". A vendor
plus a purchase DATE in a text field is enough to run an Amazon order-history
search and confirm the hit on two independent tokens.

So this dumps that bucket with the fields the search needs (recorded date, pack
count, the orig: title), and separates the ones already imaged. Everything else
here is a one-line count.
"""
import os
import re
import sys

import django
from django.db.models import Q

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from order.status_codes import PurchaseOrderStatus  # noqa: E402
from part.models import Part  # noqa: E402

EMPTY_KW = Q(keywords__isnull=True) | Q(keywords="")

active = Part.objects.filter(active=True)
imageless = active.filter(image="")
print(f"active parts          : {active.count()}")
print(f"  with image          : {active.exclude(image='').count()}")
print(f"  imageless           : {imageless.count()}")
print(f"  empty keywords      : {active.filter(EMPTY_KW).count()}  (queue D)")

# The provenance line is prose, so match on the two tokens that make it usable:
# a vendor word and a date. Anything with only one of the two is not searchable.
VIA = re.compile(r"via\s+([A-Za-z][A-Za-z0-9 .&-]{2,20})", re.I)
DATE = re.compile(r"last ordered\s+(20\d\d-\d\d-\d\d)", re.I)
PACK = re.compile(r"pack:\s*(\d+)", re.I)
ORIG = re.compile(r"orig:\s*(.+)", re.I)

print()
print("-- imageless, NO handle (no SupplierPart, no link), but prose provenance --")
rows = []
for p in imageless:
    if SupplierPart.objects.filter(part=p).exists() or p.link:
        continue
    desc = p.description or ""
    notes = p.notes or ""
    blob = f"{desc}\n{notes}"
    m_via, m_date = VIA.search(blob), DATE.search(blob)
    if not (m_via and m_date):
        continue
    rows.append((p, m_via.group(1).strip(), m_date.group(1),
                 (PACK.search(blob).group(1) if PACK.search(blob) else ""),
                 (ORIG.search(blob).group(1).strip() if ORIG.search(blob) else desc)))

rows.sort(key=lambda r: r[2], reverse=True)
for p, via, when, pack, orig in rows:
    print(f"   pk {p.pk:5d} | {via:<10} | {when} | pack={pack or '-':<5} | {p.name[:40]:<40}")
    print(f"           orig: {orig[:150]}")
print(f"   ({len(rows)} searchable)")

print()
print("-- same bucket, ALREADY imaged (control: how many the route has landed) --")
done = 0
for p in active.exclude(image=""):
    blob = f"{p.description or ''}\n{p.notes or ''}"
    if VIA.search(blob) and DATE.search(blob):
        done += 1
print(f"   {done} imaged parts carry a prose provenance line")

print()
print("-- most recent POs (queue C idempotency) --")
for po in PurchaseOrder.objects.order_by("-pk")[:8]:
    print(f"   {po.reference:<9} {PurchaseOrderStatus(po.status).label:<10} "
          f"{str(po.issue_date or po.creation_date):<12} "
          f"{(po.supplier.name if po.supplier else '?'):<18} ref={po.supplier_reference!r}")

print()
print("-- pending_decisions.md: OPEN items --")
pend = "/Volumes/4TB_Removable/inventree/pending_decisions.md"
try:
    with open(pend) as fh:
        n = 0
        for ln in fh:
            if ln.strip().startswith("- [ ]"):
                n += 1
                print(f"   {ln.rstrip()[:160]}")
        print(f"   ({n} open)")
except OSError as exc:
    print(f"   (decisions file unreadable: {exc})")
