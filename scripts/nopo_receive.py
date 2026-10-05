"""One-off historical purchases -> [ESTIMATE] stock with NO purchase order.

2026-10-04, docs/tooling-inventory.md. For purchases whose order cannot be
reconstructed whole (only a shipping notice survives, or the order mixed in
unrelated goods), so a PO would be a partial order wearing the real order
number -- the idempotency key that would later block the proper import.

    itq run scripts/nopo_receive.py <part_pk> <pieces> <unit_price|-> "<provenance>" [--commit]

Refuses if the part already has ANY stock row (that stock may be this purchase).
Provenance goes into the note after the [ESTIMATE] prefix; say vendor, order,
date and where the line came from.
"""
import argparse
import os
import sys
from decimal import Decimal

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("part", type=int)
ap.add_argument("pieces", type=float)
ap.add_argument("price")
ap.add_argument("prov")
ap.add_argument("--location", default="SLN/Machine Shop/Unfiled - Machine Shop")
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

p = Part.objects.get(pk=a.part)
dest = StockLocation.objects.get(pathstring=a.location)
rows = StockItem.objects.filter(part=p)
sp = SupplierPart.objects.filter(part=p).order_by("-pk").first()
print(f"part {p.pk} {p.name} active={p.active} rows={rows.count()} sp={sp.SKU if sp else '-'}")
if not p.active or rows.exists():
    sys.exit("REFUSE: inactive part or stock row already exists")
print(f"  -> +{a.pieces:g} @ {a.price} into {dest.pathstring}")
if a.commit:
    kw = {}
    if a.price != "-":
        kw = {"purchase_price": Decimal(a.price), "purchase_price_currency": "USD"}
    r = StockItem.objects.create(
        part=p, location=dest, quantity=a.pieces, supplier_part=sp, **kw,
        notes=(f"[ESTIMATE] PURCHASED QUANTITY, NOT A COUNT. {a.prov} No PO: the "
               "order could not be reconstructed whole. Scott 2026-10-04 chose "
               "purchase-based estimates pending a physical walk. No stocktake_date "
               "by design."))
    r.refresh_from_db()
    assert float(r.quantity) == a.pieces and r.notes.startswith("[ESTIMATE]")
    print(f"  WROTE stock item {r.pk}")
else:
    print("DRY RUN - add --commit")
