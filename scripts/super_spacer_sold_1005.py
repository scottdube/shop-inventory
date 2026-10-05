"""The 6in Super Spacer rotary table was SOLD on eBay; zero its stock row.

2026-10-05. The eBay sweep found Scott's own sale: "NEVER USED Tormach 6"
Super Spacer Motorized Rotary Table", item 167646752734, listed 2025-07-14,
paid 2025-07-21, collected by the buyer. InvenTree still held one at SLN/Machine
Shop as [CONFIRMED OWNED] (Scott 2026-08-19). Asked whether he had two; Scott
2026-10-05: "sold it".

The row is kept at 0 rather than deleted: it is the record that the package
included one and where it went. delete_on_deplete is cleared first so the save
cannot remove it.

    itq run scripts/super_spacer_sold_1005.py [--commit]
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402
from stock.models import StockItem  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

SOLD = ("SOLD on eBay 2025-07-21, item 167646752734, listed 'NEVER USED' and "
        "collected by the buyer. Scott 2026-10-05: \"sold it\". Quantity set to 0 "
        "on 2026-10-05; row kept as the record of where the package's table went.")

p = Part.objects.get(pk=569)
assert "Super Spacer" in p.name, p.name
s = StockItem.objects.get(pk=161, part=p)
print(f"{p.name}: row {s.pk} qty {float(s.quantity):g} at {s.location}")
if not a.commit:
    print("DRY RUN - add --commit")
    sys.exit()

if not s.notes.startswith("SOLD"):
    StockItem.objects.filter(pk=s.pk).update(delete_on_deplete=False, quantity=0,
                                             notes=SOLD + "\n\nPREVIOUSLY: " + s.notes)
s.refresh_from_db()
assert float(s.quantity) == 0 and s.notes.startswith("SOLD") and not s.delete_on_deplete
if "SOLD on eBay" not in (p.notes or ""):
    p.notes = (p.notes or "") + "\n\n**" + SOLD + "**"
    p.save()
    p.refresh_from_db()
    assert "SOLD on eBay" in p.notes
print(f"WROTE row {s.pk} qty {float(s.quantity):g}; part notes updated")
