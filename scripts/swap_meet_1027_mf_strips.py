"""HOT club swap meet 2026-10-27: ten tape strips of 1/4W 1% metal film resistors
into F1-R3C7, plus the strays from LRD/Receiving.

All ten values already exist as 1/4W 1% parts (the EAONE kit set at SLN), so no
new parts: LRD rows on the existing parts. Wattage from Scott's measurement
(6 mm body = 1/4W; 1/2W would be the ALLECIN set, ~9 mm). Counts are Scott's:
10 per strip, 220R is 30. Separate drawer from the carbon-film 220R/4.7k in
F1-R3C5 so the two 220Rs never mix.

Receiving strays (1k x4, 330R x2, 470R x1, stock 1080/867/868) move in too,
Scott approved. Where a stray and a strip are the same part (1k, 330R) the strip
is add_stock()ed onto the moved row: one row per part per location, provenance
in the tracking note (as the 10uF caps were merged into the priced kit row).
default_location left alone: these parts' home is the SLN kit.

Re-runnable. The first --commit died on `database is locked` (TRAPS) after six
rows; each step now checks the row before writing, so a rerun finishes only
what is missing and never adds a strip twice.

    itq run scripts/swap_meet_1027_mf_strips.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from django.core.files.base import ContentFile  # noqa: E402
from djmoney.money import Money  # noqa: E402
from common.models import Attachment, Note  # noqa: E402
from InvenTree.status_codes import StockHistoryCode  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

commit = "--commit" in sys.argv
SRC = "HOT club swap meet 2026-10-27, $0 (Scott, entered 2026-11-04)."
STRIPS = {606: 10, 631: 10, 632: 30, 611: 10, 633: 10, 615: 10, 619: 10, 634: 10, 625: 10, 630: 10}
STRAYS = {1080: 633, 867: 611, 868: 612}  # stock pk -> part pk, all in LRD/Receiving
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
rcv = StockLocation.objects.get(pathstring="LRD/Receiving")
dst = StockLocation.objects.get(pathstring="LRD/Akro Bins/F1/F1-R3C7")
STRAY_QTY = {1080: 4, 867: 2, 868: 1}
for ppk in STRIPS:
    p = Part.objects.get(pk=ppk)
    assert "1% 1/4W" in p.name and p.active, p.name
for spk, ppk in STRAYS.items():
    s = StockItem.objects.get(pk=spk)
    assert s.part_id == ppk and s.location_id in (rcv.pk, dst.pk), (spk, s.location)
held = [x.part_id for x in StockItem.objects.filter(location=dst)]
assert set(held) <= set(STRIPS) | set(STRAYS.values()), held
expect = {ppk: float(STRAY_QTY[spk]) for spk, ppk in STRAYS.items()}
for ppk, q in STRIPS.items():
    expect[ppk] = expect.get(ppk, 0) + q
for ppk, q in sorted(expect.items()):
    print(f"{Part.objects.get(pk=ppk).name}: {q:g} in F1-R3C7")
if not commit:
    raise SystemExit("DRY RUN - add --commit")

for spk in STRAYS:
    st = StockItem.objects.get(pk=spk)
    if st.location_id == rcv.pk:
        st.move(dst, "Out of Receiving into F1-R3C7 with the swap-meet strips (Scott, 2026-11-04)", u)
for ppk, q in STRIPS.items():
    row = StockItem.objects.filter(part_id=ppk, location=dst).first()
    if row and float(row.quantity) == expect[ppk]:
        print(f"  part {ppk} already done")
    elif row:
        assert float(row.quantity) + q == expect[ppk], (ppk, row.quantity)
        row.add_stock(q, u, notes=f"+{q} tape strip. {SRC}")
    else:
        s = StockItem(part_id=ppk, location=dst, quantity=q, purchase_price=Money(0, "USD"))
        s.save()
        Note.objects.create(content_object=s, title="Source", primary=True, content=f"Qty {q} (one tape strip, count from Scott). {SRC}")
        s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": float(q)}, notes=f"Into F1-R3C7. {SRC}")
if not Attachment.objects.filter(model_type="stocklocation", model_id=dst.pk).exists():
  a = Attachment(model_type="stocklocation", model_id=dst.pk, comment="Swap-meet 1/4W 1% metal film strips as received, 2026-10-27", upload_user=u)
  a.attachment.save("hot1027-mf-strips.jpg", ContentFile(open("/tmp/hot-1027-mf-strips.jpg", "rb").read()), save=True)

bad = []
for ppk, q in sorted(expect.items()):
    rows = list(StockItem.objects.filter(part_id=ppk, location=dst))
    tot = sum(float(r.quantity) for r in rows)
    print(f"part {ppk} {rows[0].part.name}: rows {[r.pk for r in rows]} qty {tot:g}")
    if len(rows) != 1 or tot != q:
        bad.append(ppk)
if StockItem.objects.filter(pk__in=STRAYS, location=rcv).exists():
    bad.append("strays")
if not Attachment.objects.filter(model_type="stocklocation", model_id=dst.pk).exists():
    bad.append("photo")
print("ALL VERIFIED" if not bad else f"NOT VERIFIED: {bad}")
