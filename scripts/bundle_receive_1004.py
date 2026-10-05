"""Tormach machine-bundle TOOLING with no stock row -> [ESTIMATE] stock, no PO.

2026-10-04, docs/tooling-inventory.md. These seven parts arrived inside the two
Tormach machine packages (quote QT123040 -> order 3000048323, 1100MX, Jan 2024;
quote QT125789 -> orders 3000059655/56, 15L, Aug 2024). Every sibling from those
bundles has a stock row; these seven never got one, so the catalogue said the
shop owns no end-mill kits, no drill set and no lathe inserts.

No PO, on purpose: both bundles were paid as DIRECTPAY lines against quotes,
and TRAPS rules those payments must never be booked as part costs. The quote
line price is quoted in the note as provenance, not written to purchase_price.

Kits and sets are ONE unit (an assortment is not a multipack). Insert 10-packs
are 10 pieces, because stock counts inserts.

Deliberately NOT received: way oil (551), coolant (557), Sikaflex (589) -
liquids from 2024, consumed; Scott's scope tonight is tooling.

    itq run scripts/bundle_receive_1004.py [--commit]
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from company.models import SupplierPart  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

dest = StockLocation.objects.get(pathstring="SLN/Machine Shop/Unfiled - Machine Shop")
Q1 = "quote QT123040 -> order 3000048323 (1100MX package, quoted 2023-12-18, ordered 2024-01-11)"
Q2 = "quote QT125789 -> orders 3000059655 + 3000059656 (15L package, 2024-08-27)"
# part, pieces, quote, quote line
PLAN = [
    (563, 1, Q1, "1 x $499.95 - a KIT, one unit"),
    (564, 1, Q1, "1 x $595.50 - a KIT, one unit"),
    (565, 1, Q1, "1 x $184.95 - a SET, one unit"),
    (572, 1, Q2, "1 x $59.50 - a kit, one unit"),
    (580, 10, Q2, "1 pack x $59.99 - 10 inserts"),
    (581, 10, Q2, "1 pack x $64.99 - 10 inserts"),
    (583, 10, Q2, "1 pack x $82.99 - 10 inserts"),
]

for pk, n, q, line in PLAN:
    p = Part.objects.get(pk=pk)
    have = StockItem.objects.filter(part=p)
    sp = SupplierPart.objects.filter(part=p, supplier__name="Tormach").first()
    print(f"part {pk} {p.name[:50]:50s} rows={have.count()} -> +{n}  sp={sp.SKU if sp else '-'}")
    if have.exists():
        print("    SKIP: already has a stock row")
        continue
    if not a.commit:
        continue
    r = StockItem.objects.create(
        part=p, location=dest, quantity=n, supplier_part=sp,
        notes=(f"[ESTIMATE] PURCHASED QUANTITY, NOT A COUNT. Arrived in the Tormach "
               f"{q}; quote line {line}. No PO: the machine packages were paid as "
               "DIRECTPAY against quotes and are never booked as part costs. Kits and "
               "inserts get used up and broken; Scott 2026-10-04 chose purchase-based "
               "estimates pending a physical walk. No stocktake_date by design."))
    r.refresh_from_db()
    assert float(r.quantity) == n and r.notes.startswith("[ESTIMATE]")
    print(f"    WROTE stock item {r.pk}")

print("COMMITTED" if a.commit else "DRY RUN - add --commit")
