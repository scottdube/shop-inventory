"""Read-only inspection of the AliExpress supplier state before the first import.

Exists because the AliExpress ruling (2026-08-28: one PO per order number under
Company #10) has to be executed against three things nobody has looked at in one
place: the placeholder PO TO-ORDER-ALI, whether the parts on today's orders
already exist, and what generate_reference() will hand out next.
"""
import os
import sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart          # noqa: E402
from order.models import PurchaseOrder, PurchaseOrderLineItem  # noqa: E402
from part.models import Part                              # noqa: E402

ali = Company.objects.filter(name__icontains="aliexpress").first()
print(f"COMPANY: pk={ali.pk} name={ali.name!r} is_supplier={ali.is_supplier}")
print(f"  SupplierParts: {SupplierPart.objects.filter(supplier=ali).count()}")

print("\nEXISTING ALIEXPRESS POs")
for po in PurchaseOrder.objects.filter(supplier=ali).order_by("pk"):
    print(f"  pk={po.pk} ref={po.reference!r} supplier_ref={po.supplier_reference!r} "
          f"status={po.get_status_display()} desc={po.description!r}")
    for ln in po.lines.all():
        sp = ln.part
        print(f"    line pk={ln.pk} qty={ln.quantity} received={ln.received} "
              f"price={ln.purchase_price} "
              f"part={sp.part.pk if sp else None}:{sp.part.name if sp else None!r} "
              f"SKU={sp.SKU if sp else None!r}")
        print(f"      line notes={ln.notes!r}")

print("\nNEXT REFERENCE")
print(f"  generate_reference() -> {PurchaseOrder.generate_reference()}")

print("\nDUPLICATE SCAN for today's two orders (1.28in TFT display)")
terms = ["TFT", "1.28", "TG820", "GC9A01", "round display"]
seen = {}
for t in terms:
    qs = Part.objects.filter(name__icontains=t) | Part.objects.filter(description__icontains=t)
    for p in qs.distinct():
        seen.setdefault(p.pk, p)
    print(f"  term {t!r}: {qs.distinct().count()} hit(s)")
for pk, p in sorted(seen.items()):
    sps = SupplierPart.objects.filter(part=p)
    print(f"  part {pk}: {p.name!r} active={p.active} cat={p.category}")
    print(f"      desc={p.description!r}")
    for sp in sps:
        print(f"      supplier={sp.supplier.name!r} SKU={sp.SKU!r}")

print("\nSKU SCAN for the four order ids")
for oid in ["8213410090415753", "8213410090395753",
            "8214467898875753", "8214467898895753"]:
    hits = SupplierPart.objects.filter(SKU__startswith=oid)
    print(f"  {oid}: {hits.count()} SupplierPart(s)")
    for sp in hits:
        print(f"      part {sp.part.pk} {sp.part.name!r} SKU={sp.SKU!r} "
              f"price={sp.get_price(1)}")
