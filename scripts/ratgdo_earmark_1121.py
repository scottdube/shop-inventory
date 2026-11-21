"""Earmark the rat-ratgdo kit for LRD on the 2027-01-03 return trip.

Same metadata shape florida.py writes ({"florida": {qty, why, added}} + the
'florida' tag), keyed by stock pk instead of part+location because SLN RB-12
holds two SHT31 rows (one at qty 0) and florida.py's .first() can pick the
empty one. Whole rows only: SLN RB-12 is the ratgdo bin and nothing in it is
shared with another project. Scott, 2026-11-21: "Add it to the trip back in
Jan".

Left out on purpose:
  - LM2596: 4 already at LRD F1-R2C1.
  - JST-XH 3-pin header: lives inside the SWANAMB kit (a location); taking 3
    of 20 is a partial earmark and that split is Scott's call.
  - 220R 0805 and JST-EH 2-pin: no stock anywhere.
  - The three built units: no stock rows exist for the Rat GDO assembly.

Dry run by default; --commit writes, then re-reads every row.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from stock.models import StockItem  # noqa: E402

COMMIT = "--commit" in sys.argv
WHY = "rat-ratgdo kit -> LRD, return trip 2027-01-03"
ADDED = "2026-11-21"
# stock pk -> expected location prefix (guards against a row having moved)
ROWS = {
    339: "SLN/Electronics Bench/Red Bins/RB-12",  # Rat GDO PCB v2.5.0 x7
    340: "SLN/Electronics Bench/Red Bins/RB-12",  # D1 Mini ESP32 x2
    688: "SLN/Electronics Bench/Red Bins/RB-12",  # SHT31-D x2
    312: "SLN/Electronics Bench/Red Bins/RB-12",  # AO3400A
    313: "SLN/Electronics Bench/Red Bins/RB-12",  # 2N7002
    314: "SLN/Electronics Bench/Red Bins/RB-12",  # 10k 0805
    315: "SLN/Electronics Bench/Red Bins/RB-12",  # 1k 0805
    316: "SLN/Electronics Bench/Red Bins/RB-12",  # PTC 500mA
    317: "SLN/Electronics Bench/Red Bins/RB-12",  # KF350 2-pos
    318: "SLN/Electronics Bench/Red Bins/RB-12",  # DB301V 3-pos
    243: "SLN/Bin Wall/A3/A3-R7C1",               # Piezo 12 mm x1
}

bad = 0
for pk, where in ROWS.items():
    s = StockItem.objects.get(pk=pk)
    path = s.location.pathstring if s.location else ""
    if path != where or float(s.quantity) <= 0:
        print(f"SKIP pk={pk}: at {path!r} qty={float(s.quantity):g}, expected {where}")
        bad += 1
        continue
    meta = s.metadata or {}
    if "florida" in meta:
        print(f"ALREADY pk={pk}: {meta['florida']}")
        continue
    print(f"{'WRITE' if COMMIT else 'would'} pk={pk} {float(s.quantity):g} x {s.part.name[:50]} @ {path}")
    if COMMIT:
        meta["florida"] = {"qty": float(s.quantity), "why": WHY, "added": ADDED,
                           "trip": "2027-01-03"}
        s.metadata = meta
        s.save()
        s.tags.add("florida")

if COMMIT:
    print("\nREAD-BACK")
    ok = 0
    for pk in ROWS:
        s = StockItem.objects.get(pk=pk)
        m = (s.metadata or {}).get("florida")
        tagged = s.tags.filter(name="florida").exists()
        good = bool(m) and m.get("trip") == "2027-01-03" and tagged
        ok += good
        print(f"  pk={pk} {'OK ' if good else 'BAD'} md={m} tag={tagged}")
    print(f"{ok}/{len(ROWS)} verified")
print(f"skipped {bad}")
