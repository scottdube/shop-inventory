"""Stock rows for the section-3 tools Scott located on 2026-11-04, plus the two he scrapped.

Qty is 1 each: Scott named one place per tool, and each was bought once (purchase-history
note: 1 unit lifetime), except the Kaisi mat, bought twice; Scott placed one, so the row
says 1 and the note says the second is unaccounted for. Not counted by hand.

Left out on purpose, waiting on Scott: solder pot #407 ("ws bottom shelf": WS1-S6 or
WS2-S6?), WG-026 leads #309 ("test equip lrd": no such LRD location yet), brush #1490
(on open PO-0288 with the Kimwipes; receive with receive_po.py, not by hand).

Scrapped (#364 helping hands, #209 desk magnifier): no stock row ever existed, so the part
is retired with active=False and a "SCRAPPED <date> (Scott)." description prefix, which
keeps it apart from merge receipts ("MERGED into ...").

Dry run by default.  itq run scripts/tool_stock_1104.py [--commit]"""
import os, sys
sys.path.insert(0, os.getcwd()); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
import django; django.setup()
from django.contrib.auth import get_user_model
from djmoney.money import Money
from common.models import Note
from InvenTree.status_codes import StockHistoryCode
from part.models import Part
from stock.models import StockItem, StockLocation
from plugins.notes_compat import note_text

COMMIT = "--commit" in sys.argv
SRC = "Located by Scott 2026-11-04 when the section-3 tools moved into Equipment; qty 1 = the one he placed, not a hand count."
BENCH, BLD3, BLD1, COUNTER = ("SLN/Electronics Bench", "SLN/Electronics Bench/BL/BL-D3",
                              "SLN/Electronics Bench/BL/BL-D1", "LRD/Countertop Wall")
LATER = " Will move to the new LRD electronics bench when it is set up (Scott)."
PLACE = [(445, BENCH, ""), (314, BLD3, ""), (201, BLD3, ""), (438, BENCH, ""),
         (316, COUNTER, LATER), (353, BENCH, " Bought twice (2 units lifetime); Scott placed one. The second is unaccounted for."),
         (315, COUNTER, LATER), (492, BLD1, "")]
SCRAP = [364, 209]

locs = {p: StockLocation.objects.get(pathstring=p) for p in {x[1] for x in PLACE}}
u = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
for pk, path, extra in PLACE:
    p = Part.objects.get(pk=pk)
    assert p.active and p.category.pathstring.startswith("Equipment/"), (pk, p.category.pathstring)
    have = StockItem.objects.filter(part=p).count()
    assert have == 0, f"#{pk} already has {have} stock rows"
    print(f"  STOCK  #{pk:5} qty 1 -> {path:34} {p.name[:50]}{'  +note' if extra else ''}")
for pk in SCRAP:
    p = Part.objects.get(pk=pk)
    assert p.active and p.stock_items.count() == 0, pk
    print(f"  SCRAP  #{pk:5} active=False  {p.name[:60]}")
if not COMMIT:
    print("DRY RUN - nothing written"); sys.exit(0)

made = []
for pk, path, extra in PLACE:
    p, loc = Part.objects.get(pk=pk), locs[path]
    s = StockItem(part=p, location=loc, quantity=1, purchase_price=Money(0, "USD"))
    s.save()
    Note.objects.create(content_object=s, title="Source", primary=True, content=SRC + extra)
    s.add_tracking_entry(StockHistoryCode.CREATED, u, deltas={"quantity": 1.0}, notes=f"Into {loc.name}. {SRC}")
    made.append((pk, path))
for pk in SCRAP:
    d = Part.objects.get(pk=pk).description or ""
    if not d.startswith("SCRAPPED"):
        Part.objects.filter(pk=pk).update(active=False, description=("SCRAPPED 2026-11-04 (Scott). " + d)[:250])

bad = []
for pk, path in made:
    rows = list(StockItem.objects.filter(part_id=pk).select_related("location"))
    if len(rows) != 1 or rows[0].location.pathstring != path or float(rows[0].quantity) != 1 or SRC[:40] not in note_text(rows[0]):
        bad.append(pk)
for pk in SCRAP:
    p = Part.objects.get(pk=pk)
    if p.active or not p.description.startswith("SCRAPPED"):
        bad.append(pk)
print("re-read problems:", bad or "none")
print("VERDICT:", "SUCCESS" if not bad and len(made) == len(PLACE) else "FAILED")
