"""Move the Digital Soldering Iron Station (part 314, stock 1261) from SLN BL-D3 to LRD.

Scott, 2026-11-05: "I have an iron here" (at LRD), and he showed the Amazon order
for this exact listing (2018-03-11, $27.99). The 2026-11-04 pass
(tool_stock_1104.py) had put it in SLN BL-D3. He named no spot at LRD, so it
goes to LRD/Countertop Wall, where its FH-300 stand (#316) and the soldering mat
(#315) already are. Rejected: LRD/Unfiled. The stand it works with is on the
countertop, so that is where it is, even though the exact spot wasn't stated.
The purchase price is set from the order ($0 placeholder before).

    itq run scripts/move_iron_314_lrd.py [--commit]
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from djmoney.money import Money  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
src = StockLocation.objects.get(pathstring="SLN/Electronics Bench/BL/BL-D3")
dst = StockLocation.objects.get(pathstring="LRD/Countertop Wall")
s = StockItem.objects.get(pk=1261)
assert s.part_id == 314 and s.location_id == src.pk and float(s.quantity) == 1, (s.part_id, s.location, s.quantity)
assert StockItem.objects.filter(part_id=314).count() == 1
stand = StockItem.objects.get(pk=1264)
assert stand.part_id == 316 and stand.location_id == dst.pk, stand.location
print(f"{s.part.name[:60]} x1: {src.pathstring} -> {dst.pathstring}; price {s.purchase_price} -> $27.99")
if "--commit" not in sys.argv:
    raise SystemExit("DRY RUN - add --commit")
s.move(dst, "At LRD, not SLN (Scott, 2026-11-05, with the 2018 Amazon order). "
            "With its FH-300 stand on the countertop; exact spot not stated.", u)
StockItem.objects.filter(pk=1261).update(purchase_price=Money("27.99", "USD"))
s = StockItem.objects.get(pk=1261)
ok = s.location_id == dst.pk and float(s.quantity) == 1 and s.purchase_price == Money("27.99", "USD")
print(f"stock {s.pk} @ {s.location.pathstring} x{s.quantity:g} price {s.purchase_price}")
print("VERDICT:", "SUCCESS" if ok else "FAILED")
