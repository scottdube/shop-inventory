"""File the 10-11 carry's generic small parts from LRD/Receiving into the F1 Akro.

Mapping is AKRO-FILL-PLAN.md v2 (~/code/docs/lrd-drawer-walk-2026-10-21/): one
kind per drawer, rows R1 dev boards, R2 modules, R3 passives, R4 switches, R5
connectors. Project-kit rows go to red bins, not here.

    itq run scripts/file_f1_1102.py                 # dry run: rows, qty, target
    itq run scripts/file_f1_1102.py --commit        # after Scott has placed them
    itq run scripts/file_f1_1102.py --commit --only 280 878   # just these

Moves with StockItem.move() so each row's history says where it went. Commuters
(metadata.commutes) are refused here: those go through trip.py land.
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

PLAN = {  # stock pk -> F1 cell
    280: "F1-R1C1", 878: "F1-R1C2",
    1075: "F1-R2C1",
    # Not from the 10-11 carry: 5 of 8 came down 2026-08-17 and sat at the bare
    # LRD root. Added when Scott pulled them out with this batch.
    64: "F1-R2C2",
    # Also unfiled at the LRD root since earlier carries (found 2026-11-02).
    66: "F1-R2C3",    # 4-ch logic level converter x13
    78: "F1-R1C3",    # AITRIP Supermini ESP32-S3 x2
    1094: "F1-R3C1",
    234: "F1-R4C1",
    1088: "F1-R5C1", 1087: "F1-R5C2", 1076: "F1-R5C2", 1073: "F1-R5C3", 1074: "F1-R5C3",
}

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
ap.add_argument("--only", type=int, nargs="*")
a = ap.parse_args()
todo = {k: v for k, v in PLAN.items() if not a.only or k in a.only}

rec = StockLocation.objects.get(pathstring="LRD/Receiving")
# Rows may also come from the bare LRD root, where pre-Receiving carries landed.
sources = {rec.pk, StockLocation.objects.get(name="LRD", parent=None).pk}
cells = {c: StockLocation.objects.get(pathstring=f"LRD/Akro Bins/F1/{c}") for c in set(todo.values())}
user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()

problems = []
for c, loc in sorted(cells.items()):
    other = StockItem.objects.filter(location=loc).exclude(pk__in=PLAN)
    if other.exists():
        problems.append(f"{c} already holds {[(s.pk, s.part.name[:30]) for s in other]}")

moved = 0
for pk, c in todo.items():
    s = StockItem.objects.select_related("part", "location").get(pk=pk)
    where = s.location.pathstring if s.location else "-"
    tag = ""
    if (s.metadata or {}).get("commutes"):
        tag = "COMMUTER - use trip.py land"
        problems.append(f"{pk} is a commuter")
    elif s.location_id == cells[c].pk:
        tag = "already there"
    elif s.location_id not in sources:
        tag = f"NOT in Receiving or LRD root ({where})"
        problems.append(f"{pk} is at {where}")
    print(f"{c:8} {pk:5} {s.quantity:>6g}  {s.part.name[:52]:52} {tag}")
    if a.commit and not tag:
        s.move(cells[c], f"Filed from {where} into F1 (AKRO-FILL-PLAN v2)", user)
        moved += 1

for p in problems:
    print("  !!", p)
if not a.commit:
    print("DRY RUN - add --commit once the parts are in their drawers")
    raise SystemExit

# Verify by re-read: .save() on this install has reported success and written nothing.
bad = [pk for pk, c in todo.items()
       if StockItem.objects.get(pk=pk).location_id != cells[c].pk]
print(f"moved {moved}; " + ("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}"))
