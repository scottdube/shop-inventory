"""Read-only census for the 2026-09-03 receiving session.

What is still outstanding on open POs, what InvenTree already knows about the
INA228 module / contactor / push buttons / flow sensor, and which locations
exist around the assembly table and Receiving. Writes nothing.

Usage:  itq run scripts/receiving_0903.py
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.db.models import F, Q  # noqa: E402

from build.models import Build  # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

print("=== OPEN PO LINES (received < quantity), non-complete POs ===")
lines = (PurchaseOrderLineItem.objects
         .filter(received__lt=F("quantity"))
         .exclude(order__status__in=[30, 40, 50])   # COMPLETE, CANCELLED, LOST
         .select_related("order", "part", "part__part")
         .order_by("order__pk", "pk"))
for ln in lines:
    po = ln.order
    sp = ln.part
    print(f"{po.reference} [{po.get_status_display()}] {str(po.supplier)[:16]:16s} "
          f"supref={str(po.supplier_reference)[:22]:22s} line={ln.pk} "
          f"qty={ln.quantity} rcvd={ln.received} price={ln.purchase_price} "
          f"target={po.target_date}")
    if sp:
        print(f"    supplier part: SKU={sp.SKU} pack_qty={sp.pack_quantity} -> "
              f"part {sp.part.pk} {sp.part.name[:70]!r}")
        print(f"       part.default_location={sp.part.default_location} "
              f"stock_rows={StockItem.objects.filter(part=sp.part).count()}")
    else:
        print("    (no supplier part)")

print()
print("=== PARTS matching the arrivals ===")
terms = ["INA228", "contactor", "MC-9b", "LA38", "push button", "pushbutton",
         "momentary", "flow sensor", "flow", "Taiss", "Baomain", "GODIY"]
seen = set()
for t in terms:
    for p in Part.objects.filter(Q(name__icontains=t) | Q(description__icontains=t)
                                 | Q(IPN__icontains=t)).order_by("pk"):
        if p.pk in seen:
            continue
        seen.add(p.pk)
        rows = StockItem.objects.filter(part=p)
        print(f"[{t}] part {p.pk}: {p.name[:80]!r}  IPN={p.IPN!r}  "
              f"cat={p.category}  default_loc={p.default_location}  active={p.active}")
        for s in rows:
            print(f"      stock {s.pk}: qty={s.quantity} loc={s.location} "
                  f"status={s.status} po={s.purchase_order} "
                  f"stocktake={s.stocktake_date} notes={str(s.notes)[:80]!r}")

print()
print("=== LOCATIONS: Assembly/Test, Receiving, shrink, project, bench ===")
for loc in StockLocation.objects.filter(
        Q(name__istartswith="AT") | Q(name__icontains="receiv") | Q(name__icontains="shrink")
        | Q(name__icontains="project") | Q(name__icontains="bench") | Q(name__icontains="assembl")
        | Q(description__icontains="shrink") | Q(description__icontains="assembl")
        | Q(description__icontains="project")).order_by("pathstring"):
    n = StockItem.objects.filter(location=loc).count()
    kids = StockLocation.objects.filter(parent=loc).count()
    print(f"loc {loc.pk}: {loc.pathstring}  name={loc.name!r}  desc={str(loc.description)[:70]!r}  "
          f"items={n} children={kids} meta={loc.metadata}")

print()
print("=== TOP-LEVEL LOCATIONS ===")
for loc in StockLocation.objects.filter(parent=None).order_by("name"):
    print(f"loc {loc.pk}: {loc.name!r} desc={str(loc.description)[:60]!r} "
          f"children={StockLocation.objects.filter(parent=loc).count()}")

print()
print("=== BUILD ORDERS / PROJECTS mentioning shrink ===")
for b in Build.objects.filter(Q(title__icontains="shrink") | Q(reference__icontains="shrink")
                              | Q(part__name__icontains="shrink")
                              | Q(notes__icontains="shrink")).order_by("pk"):
    print(f"build {b.pk} {b.reference}: {b.title!r} part={b.part.name[:60]!r} "
          f"status={b.get_status_display()}")
print("(end)")
