"""Tooling inventory baseline, 2026-10-04 -- read-only.

Scott asked for every machine tool bought to be in inventory, tooling first,
from Tormach, Lake Shore Carbide, Haas Tooling, Amazon and others. Much of it
already is (the 08-23 Tormach/MSC receives, the queue-C Haas POs), so the job is
a gap-fill and this is the "before" picture it diffs against.

Prints, per supplier company: every PO (ref, supplier_reference, date, status,
line count) and every supplier part (SKU -> part pk/name/category, stock qty).
Then every part under a tooling-ish category with no supplier part at all.
Also dumps JSON to /tmp/tooling_baseline_1004.json on the Mini for itq pull.
"""
import json
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.db.models import Sum  # noqa: E402

from company.models import Company, SupplierPart  # noqa: E402
from order.models import PurchaseOrder  # noqa: E402
from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem  # noqa: E402

VENDOR_HINTS = ("tormach", "lake", "haas", "amazon", "msc", "shars", "mcmaster",
                "precise", "maritool", "ebay", "harvey", "helical", "kennametal",
                "accupro", "yg", "mfc", "carbide", "tool", "speedtiger", "travers",
                "grainger", "zoro", "drill", "bt30", "techniks", "lyndex")

out = {"categories": [], "companies": [], "orphans": []}

print("== CATEGORIES (full tree, part counts) ==")
for c in PartCategory.objects.all().order_by("tree_id", "lft"):
    n = Part.objects.filter(category=c).count()
    path = c.pathstring
    out["categories"].append({"pk": c.pk, "path": path, "n": n})
    print(f"  {c.pk:4d} {n:4d}  {path}")

print("\n== SUPPLIERS ==")
for co in Company.objects.filter(is_supplier=True).order_by("name"):
    sps = SupplierPart.objects.filter(supplier=co).select_related("part", "part__category")
    pos = PurchaseOrder.objects.filter(supplier=co).order_by("issue_date", "creation_date")
    rec = {"pk": co.pk, "name": co.name, "pos": [], "sps": []}
    print(f"\n-- {co.pk} {co.name}: {pos.count()} POs, {sps.count()} supplier parts")
    for po in pos:
        r = {"ref": po.reference, "sref": po.supplier_reference,
             "issue": str(po.issue_date), "created": str(po.creation_date),
             "status": po.status, "lines": po.lines.count(),
             "desc": (po.description or "")[:80]}
        rec["pos"].append(r)
        print(f"   PO {r['ref']:9s} {r['sref'][:22]:22s} {r['issue']} st={r['status']} "
              f"lines={r['lines']} {r['desc']}")
    for sp in sps:
        p = sp.part
        q = StockItem.objects.filter(part=p).aggregate(s=Sum("quantity"))["s"] or 0
        r = {"sp": sp.pk, "sku": sp.SKU, "part": p.pk, "name": p.name,
             "cat": p.category.pathstring if p.category else "", "active": p.active,
             "stock": float(q), "pack": str(sp.pack_quantity)}
        rec["sps"].append(r)
        print(f"   sp{sp.pk:5d} {sp.SKU[:28]:28s} part {p.pk:5d} "
              f"{'' if p.active else '[INACTIVE] '}{p.name[:60]} | {r['cat']} | stk {q}")
    out["companies"].append(rec)

print("\n== PARTS IN TOOLING-ISH CATEGORIES WITH NO SUPPLIER PART ==")
tool_cats = [c for c in PartCategory.objects.all()
             if any(k in c.pathstring.lower() for k in
                    ("tool", "endmill", "end mill", "drill", "tap", "insert", "holder",
                     "machin", "collet", "cutter", "mill", "lathe"))]
for c in tool_cats:
    for p in Part.objects.filter(category=c):
        if not SupplierPart.objects.filter(part=p).exists():
            q = StockItem.objects.filter(part=p).aggregate(s=Sum("quantity"))["s"] or 0
            out["orphans"].append({"part": p.pk, "name": p.name, "cat": c.pathstring,
                                   "stock": float(q), "active": p.active})
            print(f"   part {p.pk:5d} {p.name[:70]} | {c.pathstring} | stk {q}")

with open("/tmp/tooling_baseline_1004.json", "w") as f:
    json.dump(out, f, indent=1, default=str)
print("\nwrote /tmp/tooling_baseline_1004.json")
