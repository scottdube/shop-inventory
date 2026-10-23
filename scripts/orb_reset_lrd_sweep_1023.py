"""Companion to orb_reset_test_passives_1023.py: every LRD stock row whose part
looks like a passive or diode, in ANY category.

The first script searched resistor/capacitor/diode categories only; a kit filed
elsewhere (e.g. under a Kits root) would have been missed. Read-only.
"""

import os
import re
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockItem, StockLocation  # noqa: E402

RX = re.compile(r"resist|capac|diode|schottky|1n4|bat5|ohm|\buf\b|µf|electrolytic|passive", re.I)

lrd = StockLocation.objects.get(parent=None, name="LRD")
locs = lrd.get_descendants(include_self=True)
rows = StockItem.objects.filter(location__in=locs).select_related("part", "location")
n = 0
for s in rows.order_by("location__pathstring", "part__name"):
    p = s.part
    cat = p.category.pathstring if p.category else ""
    if RX.search(p.name or "") or RX.search(p.description or "") or RX.search(cat):
        n += 1
        print(f"{float(s.quantity):g} x {p.name[:70]}  [part/{p.pk} stock/{s.pk}] "
              f"active={p.active}\n    @ {s.location.pathstring}  cat={cat}")
print(f"\n{n} matching row(s) of {rows.count()} LRD stock rows scanned")
