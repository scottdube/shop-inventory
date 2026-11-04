"""Move the remaining five 11-02 project kits from LRD/Receiving into their LRD red bins.

Scott, 2026-11-04, asked whether the other kits went into their marked bins on
11-03 like the G1000: "Yes, all of them". Bins and rows are the 11-02 list in
~/code/docs/lrd-drawer-walk-2026-10-21/AKRO-FILL-PLAN.md. default_location is
not touched (a project bin is never a spare's home).

    itq run scripts/lrd_kits_to_red_bins.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

KITS = {
    "RB-03": ("MAILBOX MESHTASTIC NODE kit (BO-0001)", [277, 1083, 1084]),
    "RB-04": ("VOICE ASSISTANT NODE kit (BO-0005)", [1, 4, 278, 279]),
    "RB-07": ("BENCH POWER SUPPLY kit (BO-0004)", [107, 288]),
    "RB-10": ("INFO ORBS kit (BO-0016)", [796, 1216]),
    "RB-14": ("AC WALL ADAPTER FOR IoT kit (BO-0018)", [607, 608, 609, 610, 611, 1079, 1080, 1081, 1082]),
}
TAIL = " Loaded 2026-11-03 (Scott, recorded 2026-11-04). Holds ONE project's kit OR free storage - never both."
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
rcv = StockLocation.objects.get(pathstring="LRD/Receiving")
plan = []
for name, (title, rows) in KITS.items():
    rb = StockLocation.objects.get(pathstring=f"LRD/Electronics Bench/Red Bins/{name}")
    # Idempotent (a "database is locked" mid-run must be safe to rerun): the bin
    # may hold only this kit's rows, and each row is in Receiving or already here.
    other = StockItem.objects.filter(location=rb).exclude(pk__in=rows)
    assert not other.exists(), f"{name} holds other rows {list(other.values_list('pk', flat=True))}"
    for pk in rows:
        s = StockItem.objects.get(pk=pk)
        assert s.location_id in (rcv.pk, rb.pk), (pk, s.location)
        print(f"{name} <- {pk} {s.part.name[:50]} x{s.quantity:g}")
    plan.append((rb, title, rows))
if "--commit" not in sys.argv:
    raise SystemExit("DRY RUN - add --commit")
bad = []
for rb, title, rows in plan:
    for pk in rows:
        if StockItem.objects.get(pk=pk).location_id == rb.pk:
            continue
        StockItem.objects.get(pk=pk).move(rb, f"Kit loaded into {rb.name} on 2026-11-03 (Scott, entered 2026-11-04)", u)
    StockLocation.objects.filter(pk=rb.pk).update(description=title + "." + TAIL)
    n = StockItem.objects.filter(pk__in=rows, location=rb).count()
    print(f"{rb.name}: {n}/{len(rows)} | {StockLocation.objects.get(pk=rb.pk).description[:45]}")
    if n != len(rows):
        bad.append(rb.name)
s = StockItem.objects.get(pk=1080)
s.notes.filter(title="Identified").update(content=(
    "IDENTIFIED 2026-11-04: AC Wall Adapter for IoT kit (BO-0018), per the 11-02 LRD fill plan. "
    "Loaded into LRD RB-14 on 2026-11-03 (Scott). Supersedes the UNLOCATED note written the same day."))
print("1080 note:", s.notes.filter(title="Identified").first().content[:90])
if "RB-14" not in s.notes.filter(title="Identified").first().content:
    bad.append("1080 note")
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
