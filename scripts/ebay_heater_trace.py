"""Trace the eBay 3000W induction heater order: does its stock exist, and is there a PO?

Scott says the order landed and was exploded into component parts. po_check said
'absent' for every spelling of eBay order 09-14960-44072. Both can be true — that
is the po-check-hyphen-blind failure mode. This says which.

Read-only.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem  # noqa: E402

TERMS = ["induction", "zvs", "heater", "ammeter", "53v", "3000w"]

print("=== PARTS matching induction-heater terms ===")
seen = set()
for t in TERMS:
    for p in Part.objects.filter(name__icontains=t) | Part.objects.filter(
        description__icontains=t
    ):
        if p.pk in seen:
            continue
        seen.add(p.pk)
        qty = sum(si.quantity for si in StockItem.objects.filter(part=p))
        print(f"  [{t:9s}] part {p.pk:5d} {p.name[:52]:52s} qty={qty} active={p.active}")
if not seen:
    print("  (none)")

print("\n=== SUPPLIER PARTS whose SKU/link mentions the item or order ===")
hits = 0
for sp in SupplierPart.objects.all():
    blob = f"{sp.SKU} {sp.link or ''} {sp.note or ''}".lower()
    if "286924140726" in blob or "14960" in blob or "induction" in blob:
        hits += 1
        print(f"  SP {sp.pk:5d} supplier={str(sp.supplier)[:22]:22s} SKU={sp.SKU[:34]:34s} part={sp.part}")
if not hits:
    print("  (none)")

print("\n=== PURCHASE ORDERS from any eBay-ish supplier ===")
ebay = Company.objects.filter(name__icontains="ebay")
print(f"  eBay companies: {[ (c.pk, c.name) for c in ebay ] or 'NONE'}")
for po in PurchaseOrder.objects.filter(supplier__in=ebay).order_by("pk"):
    print(
        f"  {po.reference:10s} supplier_ref={str(po.supplier_reference)[:26]:26s} "
        f"{po.get_status_display():10s} lines={po.lines.count()} issued={po.issue_date}"
    )

print("\n=== ANY PO whose supplier_reference contains 14960 (loose) ===")
loose = 0
for po in PurchaseOrder.objects.all():
    ref = (po.supplier_reference or "") + " " + (po.reference or "")
    if "14960" in ref.replace("-", "").replace(" ", "") or "14960" in ref:
        loose += 1
        print(f"  {po.reference} supplier_ref={po.supplier_reference!r} supplier={po.supplier}")
if not loose:
    print("  (none)")

print("\n=== MFC company / supplier check ===")
for c in Company.objects.filter(name__icontains="mfc"):
    npo = PurchaseOrder.objects.filter(supplier=c).count()
    print(f"  company {c.pk:4d} {c.name!r} is_supplier={c.is_supplier} POs={npo}")
    for po in PurchaseOrder.objects.filter(supplier=c).order_by("pk"):
        print(
            f"      {po.reference:10s} supplier_ref={str(po.supplier_reference)[:26]:26s} "
            f"{po.get_status_display():10s} lines={po.lines.count()} issued={po.issue_date}"
        )
if not Company.objects.filter(name__icontains="mfc").exists():
    print("  (no company matching 'mfc')")
