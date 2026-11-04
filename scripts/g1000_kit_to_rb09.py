"""Move the Sim G1000 PFD kit (BO-0017) from LRD/Receiving into LRD RB-09.

Scott, 2026-11-04: "we put it in RB yesterday". RB-09 is the bin the 11-02 list
sent to Scott marked for G1000 (AKRO-FILL-PLAN.md; empty at SLN, so no false
twin). Rows are the plan's G1000 line plus the four PCBs (741-744) the plan says
belong to the kit. default_location is not touched: a project bin is never a
spare's home.

Also corrects stock 1080 (1k x4): it is the AC Wall Adapter kit's 1k (BO-0018,
same plan table), not an unknown stray. It stays in Receiving until Scott says
which bin that kit went in.

    itq run scripts/g1000_kit_to_rb09.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

ROWS = [741, 742, 743, 744, 748, 749, 844, 859, 861, 862, 865, 867, 868, 873, 1077, 1078]
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
rcv = StockLocation.objects.get(pathstring="LRD/Receiving")
rb = StockLocation.objects.get(pathstring="LRD/Electronics Bench/Red Bins/RB-09")
assert not StockItem.objects.filter(location=rb).exists(), "RB-09 not empty"
for pk in ROWS:
    s = StockItem.objects.get(pk=pk)
    assert s.location_id == rcv.pk, (pk, s.location)
    print(f"{pk} {s.part.name[:55]} x{s.quantity:g}")
if "--commit" not in sys.argv:
    raise SystemExit("DRY RUN - add --commit")
for pk in ROWS:
    StockItem.objects.get(pk=pk).move(rb, "G1000 kit loaded into RB-09 on 2026-11-03 (Scott, entered 2026-11-04)", u)
StockLocation.objects.filter(pk=rb.pk).update(description=(
    "SIM G1000 PFD kit (BO-0017, build #3 at LRD, returns to SLN for install). Loaded 2026-11-03 "
    "(Scott). Includes the four FSD/Peter Eier PCBs (741-744). Holds ONE project's kit OR free storage - never both."))
s = StockItem.objects.get(pk=1080)
s.notes.filter(title="Unlocated").update(title="Identified", content=(
    "IDENTIFIED 2026-11-04: AC Wall Adapter for IoT kit (BO-0018), per the 11-02 LRD fill plan. "
    "Supersedes the UNLOCATED note written the same day. Proposed bin LRD RB-14; not yet confirmed."))
moved = StockItem.objects.filter(pk__in=ROWS, location=rb).count()
print(f"in RB-09: {moved}/{len(ROWS)} | RB-09 desc: {StockLocation.objects.get(pk=rb.pk).description[:40]} | "
      f"1080 notes: {[n.title for n in StockItem.objects.get(pk=1080).notes.all()]}")
print("ALL VERIFIED" if moved == len(ROWS) else "NOT VERIFIED")
