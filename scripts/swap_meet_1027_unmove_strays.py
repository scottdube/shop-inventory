"""Undo the stray-resistor part of swap_meet_1027_mf_strips.py.

Scott, 2026-11-04, on the 1k x4 / 330R x2 / 470R x1 moved out of LRD/Receiving:
"I don't see those anywhere. I don't even remember that." They are the EAONE
Florida-bag splits (2026-09-20 / 10-08) that transfer order 1 booked into
LRD/Receiving on 11-02. The move into F1-R3C7 was made on the record alone;
nobody had them in hand. So they go back to LRD/Receiving, the record's last
claim, marked UNLOCATED (there is no LRD Unfiled location), and are not asked
about again.

The 1k and 330R rows had the swap-meet strip (+10) add_stock()ed onto them.
splitStock() peels the 10 off into a new row that STAYS in F1-R3C7; the old row,
carrying the stray's notes and history, is what goes back.

    itq run scripts/swap_meet_1027_unmove_strays.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from djmoney.money import Money  # noqa: E402
from common.models import Note  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

SRC = "HOT club swap meet 2026-10-27, $0 (Scott, entered 2026-11-04)."
UNLOC = ("UNLOCATED 2026-11-04: Scott does not see these and does not remember them. "
         "Booked here by transfer order 1 (2026-11-02); never confirmed in hand at LRD. Do not re-ask.")
ROWS = {1080: (633, 4, 10), 867: (611, 2, 10), 868: (612, 1, 0)}  # stock -> (part, stray qty, strip qty)
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
dst = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R3C7")
rcv = StockLocation.objects.get(pathstring="LRD/Receiving")
for spk, (ppk, sq, tq) in ROWS.items():
    s = StockItem.objects.get(pk=spk)
    assert s.part_id == ppk and s.location_id == dst.pk and float(s.quantity) == sq + tq, (spk, s.location, s.quantity)
    print(f"{s.part.name}: {tq} stay in F1-R3C7, {sq} back to Receiving (UNLOCATED)")
if "--commit" not in sys.argv:
    raise SystemExit("DRY RUN - add --commit")
for spk, (ppk, sq, tq) in ROWS.items():
    s = StockItem.objects.get(pk=spk)
    if tq:
        new = s.splitStock(tq, dst, u, notes=f"Swap-meet strip split back off the stray row. {SRC}")
        new = StockItem.objects.get(pk=new.pk)
        StockItem.objects.filter(pk=new.pk).update(purchase_price=Money(0, "USD"))
        Note.objects.create(content_object=new, title="Source", primary=True,
                            content=f"Qty {tq} (one tape strip, count from Scott). {SRC}")
    s = StockItem.objects.get(pk=spk)
    s.move(rcv, UNLOC, u)
    Note.objects.create(content_object=s, title="Unlocated", primary=False, content=UNLOC)
bad = []
for spk, (ppk, sq, tq) in ROWS.items():
    s = StockItem.objects.get(pk=spk)
    here = list(StockItem.objects.filter(part_id=ppk, location=dst))
    print(f"part {ppk}: stray row {spk} @ {s.location.name} x{s.quantity:g} | F1-R3C7 rows {[(h.pk, float(h.quantity), str(h.purchase_price)) for h in here]}")
    if s.location_id != rcv.pk or float(s.quantity) != sq or sum(float(h.quantity) for h in here) != tq:
        bad.append(spk)
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
