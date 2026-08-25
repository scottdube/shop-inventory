"""Move the MEANLIN gauge from RB-21 into RB-17, joining the vacuum sensor.

Scott, 2026-08-25: "probably should move to seventeen with the vacuum pressure
sensor." One project, one bin -- which is the rack's own rule, and it frees
RB-21. Uses StockItem.move() rather than a queryset update so the transfer
lands in the item's tracking history; a bare .update(location=) would relocate
the row with no record that it ever sat in RB-21.
"""
import os, sys, django
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model
from stock.models import StockItem, StockLocation

COMMIT = "--commit" in sys.argv
TODAY = date.today()
user = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()

si = StockItem.objects.get(pk=678)
rb17 = StockLocation.objects.get(name="RB-17")
rb21 = StockLocation.objects.get(name="RB-21")

print(f"stock #{si.pk} {si.part.name[:60]}")
print(f"  {si.location.pathstring} -> {rb17.pathstring}")

others = StockItem.objects.filter(location=rb21).exclude(pk=si.pk)
print(f"  other rows left in RB-21: {others.count()}")

RB17 = ("VACUUM CONTROLLER project - the whole kit, both halves now in one bin. "
        "(1) MPXV6115VC6U vacuum sensor #107, 0 to -115 kPa, ported SOP-8, in "
        "anti-static. It measures NEGATIVE pressure only and is NOT "
        "interchangeable with the positive-pressure 1/8 NPT transducers in "
        "B3-R7C2. (2) MEANLIN 3in dial gauge #1097, lower mount, boxed new - "
        "RANGE UNREAD, and a positive-only dial cannot read vacuum, so read the "
        "dial before designing around it. Gauge moved in from RB-21 2026-08-25 "
        "on Scott's call: one project, one bin, and it frees RB-21.")
RB21 = (f"VERIFIED EMPTY {TODAY} - held the MEANLIN vacuum-project gauge until "
        "2026-08-25, when it moved to RB-17 to sit with the rest of that "
        "project's kit.")

if not COMMIT:
    print("\n  DRY RUN - add --commit")
    sys.exit()

si.move(rb17, "Consolidating the Vacuum Controller kit into RB-17 (Scott, "
              "2026-08-25 Red Bin walk).", user)

StockLocation.objects.filter(pk=rb17.pk).update(description=RB17)
StockLocation.objects.filter(pk=rb21.pk).update(description=RB21)

si = StockItem.objects.get(pk=si.pk)
left = StockItem.objects.filter(location=rb21).count()
print(f"\n  stock #{si.pk} now @ {si.location.pathstring}")
print(f"  rows left in RB-21: {left}")
print("  RB-17:", "OK" if StockLocation.objects.get(pk=rb17.pk).description == RB17 else "MISMATCH")
print("  RB-21:", "OK" if StockLocation.objects.get(pk=rb21.pk).description == RB21 else "MISMATCH")
print("  MOVE VERIFIED" if si.location_id == rb17.pk and left == 0 else "  CHECK THIS")
