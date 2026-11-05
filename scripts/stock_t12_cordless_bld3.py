"""Stock the battery soldering iron in SLN BL-D3: part 731, the T12 DIY station kit.

Scott, 2026-11-05: the iron in BL-D3 is the one he built from the AliExpress
T12 controller kit "according to an instructables article ... to use a
milwaukee battery". #731 already existed (purchase history imported) and had
no stock row, so this stocks it there. No new part is created. The 11-04
pass had put the corded #314 in BL-D3, which is how the gap stayed hidden.

The part is renamed once, to say what it now is. The AliExpress listing title
moves into the description. The Milwaukee pack size (M12 or M18) and the article
weren't stated, so they aren't recorded.
Rejected: a new "battery iron" part, which would duplicate #731.

Price: two orders from the same store. The kit was $14.19. The shell was
$10.85 less a $2.05 partial refund (kept, not returned). Net $22.99.

    itq run scripts/stock_t12_cordless_bld3.py [--commit]
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from djmoney.money import Money  # noqa: E402
from InvenTree.status_codes import StockHistoryCode  # noqa: E402
from common.models import Note  # noqa: E402
from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

NAME = "T12 Cordless Soldering Iron (DIY kit build, Milwaukee battery)"
DESC = ("T12 controller kit built into a cordless iron on a Milwaukee power-tool battery "
        "(Instructables build). Bought as 'T12 Digital Soldering Iron Station Temperature "
        "Controller Kit' + ABS shell. Takes T12 tips, e.g. the CNC Kitchen set (#854).")
PRICE = Money("22.99", "USD")

u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
loc = StockLocation.objects.get(pathstring="SLN/Electronics Bench/BL/BL-D3")
p = Part.objects.get(pk=731)
assert p.active and "T12" in p.name, p.name
assert not StockItem.objects.filter(part=p).exists(), "731 already has stock"
assert not Part.objects.filter(name=NAME).exclude(pk=731).exists()
print(f"part 731 '{p.name}' -> '{NAME}'")
print(f"stock x1 @ {loc.pathstring} price {PRICE}; drawer now holds "
      f"{list(StockItem.objects.filter(location=loc).values_list('pk', 'part__name'))}")
if "--commit" not in sys.argv:
    raise SystemExit("DRY RUN - add --commit")

Part.objects.filter(pk=731).update(name=NAME, description=DESC[:250], default_location=loc)
s = StockItem(part_id=731, location=loc, quantity=1, purchase_price=PRICE)
s.save()
Note.objects.create(content_object=s, title="Source", primary=True, content=(
    "Identified by Scott 2026-11-05: built from the AliExpress T12 kit per an Instructables "
    "article to run on a Milwaukee battery. Price = kit $14.19 + shell $10.85 - $2.05 partial refund."))
s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 1.0}, notes="Into BL-D3.")

s = StockItem.objects.get(pk=s.pk)
p = Part.objects.get(pk=731)
ok = (p.name == NAME and p.default_location_id == loc.pk and s.location_id == loc.pk
      and float(s.quantity) == 1 and s.purchase_price == PRICE)
print(f"stock {s.pk}: part {p.pk} {p.name} x{s.quantity:g} @ {s.location.pathstring} {s.purchase_price}")
print("VERDICT:", "SUCCESS" if ok else "FAILED")
