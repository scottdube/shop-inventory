"""Do the three 2025 Tormach orders and the 2025 MSC order have their cost captured?

The task file lists these four as already imported, but qb_vendor_pos_0902.py
found no PO for any of them. "Imported" for queue B means the COST landed --
supplier part, price break, part pricing -- which can be true with no PO at all
(import_haas.py works that way). So look at the actual SKUs before concluding
anything either way.

Read-only.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem  # noqa: E402

# sku, qty ordered, EXTENDED price from the email, description
LINES = [
    ("3000069522", "38412", 1, "3350.00", "microARC 4 - 100 mm 4th Axis"),
    ("3000069522", "52643", 1, "129.95", "microARC 4 Subplate"),
    ("3000069522", "38954", 1, "289.95", "4th Axis Driver and Installation Kit (M/MX)"),
    ("3000069852", "34697", 1, "94.95", '1/2 in. x 1-1/4 in. x 1/2 in. Thread Mill'),
    ("3000069852", "34696", 1, "70.95", '3/8 in. x 1 in. x 3/8 in. Thread Mill'),
    ("3000069852", "34695", 1, "58.95", '5/16 x 3/4 in. x 5/16 in. Thread Mill'),
    ("3000070065", "35724", 1, "44.95", "4 Inch Length Coolant Nozzle for Turret 10-Pack"),
    ("3000070065", "32624", 3, "61.47", "Aluminum Fixture Plate, 20 x 9.5 x 10mm"),
    ("3000070065", "53400", 2, "41.90", "Tormach Branded T-shirt Green (APPAREL - rule 7, do not create)"),
    ("251613620", "89629687", 1, "556.20", "210GPH TRANSPARENT OIL SKIMMER"),
    ("251613620", "82976713", 1, "80.38", "1/2X1/2X2X4 ZIR 3FL CARB HP 40D CC SEM"),
]

print(f"{'order':11s} {'sku':10s} qty {'unit':>9s}  state")
for order, sku, qty, ext, desc in LINES:
    unit = float(ext) / qty
    sp = SupplierPart.objects.filter(SKU=sku).first()
    if not sp:
        print(f"{order:11s} {sku:10s} {qty:3d} {unit:9.2f}  NO SUPPLIER PART   | {desc[:46]}")
        continue
    breaks = [(str(b.quantity), str(b.price)) for b in sp.pricebreaks.all()]
    stock = [(si.pk, str(si.quantity), str(si.purchase_price)) for si in
             StockItem.objects.filter(supplier_part=sp)]
    print(f"{order:11s} {sku:10s} {qty:3d} {unit:9.2f}  sp={sp.pk} part={sp.part.pk} "
          f"pack={sp.pack_quantity!r} breaks={breaks} stock={stock} | {sp.part.name[:40]}")

print("\n=== name-token dedup check (would a part already exist under another name?) ===")
for token in ["microARC", "Thread Mill", "Fixture Plate", "Coolant Nozzle", "Skimmer", "Subplate"]:
    hits = (Part.objects.filter(name__icontains=token) |
            Part.objects.filter(description__icontains=token)).distinct()
    print(f"  {token!r}: {hits.count()}")
    for p in hits[:10]:
        print(f"      pk={p.pk:4d} {p.name[:58]!r}")
