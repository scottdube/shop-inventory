"""Read-only: resolve Scott's 2026-11-04 location words for the 13 stockless tools to
StockLocation rows, and show lifetime purchase units per tool and PO-0288's state.
Run: itq run scripts/tool_locs_probe_1104.py"""
import os, sys, re
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django; django.setup()
from django.db.models import Q
from stock.models import StockLocation, StockItem
from part.models import Part
from order.models import PurchaseOrder
from plugins.notes_compat import note_text

for pat in ("bench", "BL-3", "BL 3", "BL-D1", "shelf", "WS", "workstation", "countertop", "test equip", "Cab2-D2", "Cab2"):
    rows = StockLocation.objects.filter(Q(name__icontains=pat) | Q(pathstring__icontains=pat)).order_by("pathstring")[:12]
    print(f"\n[{pat}]")
    for l in rows:
        print(f"   {l.pk:5} {l.pathstring}  ({l.stock_items.count()} rows)")
print("\nwhere existing tools sit:")
for s in StockItem.objects.filter(part_id__in=[474, 311, 853]).select_related("location"):
    print("  ", s.part_id, s.quantity, s.location.pathstring if s.location else "-")
print("\nlifetime purchase units (from purchase-history note):")
for pk in [445, 314, 407, 201, 438, 316, 353, 315, 364, 209, 309, 492, 1490]:
    p = Part.objects.get(pk=pk)
    m = re.search(r"(\d+) purchases?, (\d+) units? lifetime", note_text(p))
    print(f"   #{pk:5} active={p.active} {m.group(0) if m else '-':32} {p.name[:50]}")
po = PurchaseOrder.objects.get(reference="PO-0288")
print(f"\nPO-0288 {po.supplier.name} status={po.status} lines:")
for l in po.lines.all().select_related("part__part"):
    print(f"   {l.part.part_id if l.part else '-'} qty={l.quantity:g} recv={l.received:g} {l.part.part.name[:50] if l.part else ''}")
