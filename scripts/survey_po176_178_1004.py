"""Read-only: PO-0176 (seller-cancelled) and PO-0178 (toy, not inventory), 2026-10-04."""
import os, sys, django
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings"); django.setup()
from order.models import PurchaseOrder
from stock.models import StockItem
from part.models import Part
for r in ("PO-0176", "PO-0178"):
    p = PurchaseOrder.objects.get(reference=r)
    print(f"{r} status={p.status} {p.supplier.name} {p.supplier_reference}\n  desc: {p.description}\n  notes: {(p.notes or '')[:300]!r}")
    for l in p.lines.all():
        sp = l.part; pt = sp.part if sp else None
        print(f"  line {l.pk} SP#{sp.pk if sp else None} {sp.SKU if sp else ''} qty {float(l.quantity)} recv {float(l.received)} price {l.purchase_price}")
        if pt:
            others = l.part.part.supplier_parts.exclude(pk=sp.pk).count()
            pos = set(pt.supplier_parts.values_list("purchase_order_line_items__order__reference", flat=True))
            print(f"    part #{pt.pk} {pt.name!r} active={pt.active} stock_rows={StockItem.objects.filter(part=pt).count()} "
                  f"other_SPs={others} POs={sorted(x for x in pos if x)}\n    part desc: {pt.description!r}")
