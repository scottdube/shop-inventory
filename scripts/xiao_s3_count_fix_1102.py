"""Correct the XIAO ESP32-S3 spare count at F1-R1C3 (stock 1215) from 1 to 2, 2026-11-02.

Scott, after xiao_s3_lrd_1102.py ran: "a total of 3, so there's 2 left over and 1
being put in the new version of the info orbs board". His earlier "Qty 2, 1 going"
was read as 2 in all; it was 2 spare plus the orb one. Stock 1216 (the orb board,
x1) is right as it stands. Added with add_stock rather than overwriting the
quantity, so the history shows the correction.

    itq run scripts/xiao_s3_count_fix_1102.py [--commit]
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from stock.models import StockItem  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
s = StockItem.objects.get(pk=1215)
assert s.part_id == 101 and s.location.pathstring == "LRD/Akro Bins/F1/F1-R1C3", (s.part_id, s.location)
assert s.quantity == 1, f"already {s.quantity}"
print(f"stock 1215 x{s.quantity:g} -> x2; stock 1216 stays x{StockItem.objects.get(pk=1216).quantity:g}")
if not a.commit:
    raise SystemExit("DRY RUN - add --commit")

s.add_stock(1, u, notes="Count correction (Scott): 3 found in all, 2 spare here + 1 for Info Orb v2 (stock 1216).")
s = StockItem.objects.get(pk=1215)
print(f"stock 1215 x{s.quantity:g} @ {s.location.pathstring}")
print("ALL VERIFIED" if s.quantity == 2 else "NOT VERIFIED")
