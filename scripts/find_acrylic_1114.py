"""Read-only: every part, PO line and stock row that looks like acrylic sheet."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.db.models import Q
from part.models import Part
from stock.models import StockItem
from order.models import PurchaseOrderLineItem

terms = ("acrylic", "plexi", "pmma", "perspex", "lexan", "polycarbonate", "kinlink", "art3d")
q = Q()
for t in terms:
    q |= Q(name__icontains=t) | Q(description__icontains=t) | Q(keywords__icontains=t)
rows = Part.objects.filter(q).order_by("pk")
print(f"parts matching {terms}: {rows.count()} (all printed)")
for p in rows:
    print(f"\npk={p.pk} active={p.active} stock={p.total_stock:g} {p.name!r}\n   desc={p.description!r}")
    for s in StockItem.objects.filter(part=p):
        print(f"   stock qty={s.quantity:g} loc={s.location.pathstring if s.location else None!r}")
    for li in PurchaseOrderLineItem.objects.filter(part__part=p).select_related("order"):
        print(f"   PO {li.order.reference} supplier_ref={li.order.supplier_reference!r} "
              f"qty={li.quantity:g} recv={li.received:g} status={li.order.status} date={li.order.creation_date}")
lq = Q()
for t in terms:
    lq |= Q(notes__icontains=t) | Q(reference__icontains=t)
for li in PurchaseOrderLineItem.objects.filter(lq).select_related("order"):
    print(f"\nPO line (by text) {li.order.reference}: {li.reference!r} notes={li.notes!r} part={li.part}")
