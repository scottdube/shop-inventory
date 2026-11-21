"""Earmark 3 of the 20 JST-XH 3-pin headers (stock pk 325, inside the SWANAMB
kit) for the rat-ratgdo kit's 2027-01-03 trip to LRD. Partial earmark, Scott's
call 2026-11-21: "Yes, add 3". Same metadata shape as ratgdo_earmark_1121.py.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockItem  # noqa: E402

s = StockItem.objects.get(pk=325)
assert s.part_id == 875, s.part_id
assert float(s.quantity) >= 3, s.quantity
meta = s.metadata or {}
assert "florida" not in meta, meta
meta["florida"] = {"qty": 3.0, "why": "rat-ratgdo kit -> LRD, return trip 2027-01-03",
                   "added": "2026-11-21", "trip": "2027-01-03"}
s.metadata = meta
s.save()
s.tags.add("florida")

r = StockItem.objects.get(pk=325)
m = (r.metadata or {}).get("florida")
tagged = r.tags.filter(name="florida").exists()
print(f"{'OK' if m and m['qty'] == 3.0 and tagged else 'BAD'} pk=325 "
      f"{m} of {float(r.quantity):g} @ {r.location.pathstring} tag={tagged}")
