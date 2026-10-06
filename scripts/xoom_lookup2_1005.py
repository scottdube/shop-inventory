"""Read-only: detail on the probe-related parts already in InvenTree, and Equipment/CNC/Accessories."""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from company.models import SupplierPart
from order.models import PurchaseOrderLineItem
from part.models import Part, PartCategory
from stock.models import StockItem
for pk in (567, 1344, 1161):
    p = Part.objects.get(pk=pk)
    print(f"\n#### part #{p.pk} {p.name!r}\n  cat={p.category.pathstring} IPN={p.IPN!r} created={p.creation_date} default_loc={p.default_location}")
    print(f"  desc={p.description!r}\n  keywords={p.keywords!r}\n  notes={(p.notes or '')[:1200]!r}")
    for sp in SupplierPart.objects.filter(part=p):
        print(f"  SP #{sp.pk} {sp.supplier.name} SKU={sp.SKU!r} pack={sp.pack_quantity} link={sp.link}")
        for li in PurchaseOrderLineItem.objects.filter(part=sp):
            print(f"    PO {li.order.reference} {li.order.supplier_reference} {li.order.issue_date} qty={li.quantity} @ {li.purchase_price} status={li.order.status}")
    for s in StockItem.objects.filter(part=p):
        print(f"  STOCK #{s.pk} qty={s.quantity} loc={s.location.pathstring if s.location else None} status={s.status} serial={s.serial!r} batch={s.batch!r} updated={s.updated}\n    notes={(s.notes or '')[:600]!r}")
print("\n#### Equipment/CNC/Accessories (#87) and Equipment/CNC/Mills (#93), Machine Accessories (#48)")
for cpk in (87, 93, 48):
    c = PartCategory.objects.get(pk=cpk)
    print(f"-- {c.pathstring}")
    for p in c.parts.order_by("pk"):
        st = sum(s.quantity for s in StockItem.objects.filter(part=p))
        locs = {s.location.pathstring for s in StockItem.objects.filter(part=p) if s.location}
        print(f"  #{p.pk} {p.name[:70]!r} stock={st} {sorted(locs)}")
