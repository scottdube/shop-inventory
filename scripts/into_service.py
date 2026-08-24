"""Take a consumable out of the bin and put it INTO SERVICE on a tool.

Scott, 2026-08-24: *"we need to set up a process that when we take it out of the
bin and put it on the gun — that's true with any consumable — then we've used
it, and then we don't have one in stock anymore. We're really just talking about
spares being in stock."*

That last sentence is the whole model: **stock means SPARES.** A nozzle fitted
to the gun, a collet in the spindle, a filter in the housing — owned, findable,
and not a spare. `StockItem.belongs_to` says exactly that, and it is the first
clause of `IN_STOCK_FILTER`, so an installed item stops counting toward
`get_stock_count()` and `minimum_stock` starts telling the truth.

Why not just delete the row or zero it out. Because "we've used it" and "it no
longer exists" are different, and the difference is what you need six months
later when the gun stops pulling and somebody asks what is actually fitted to
it. Consuming discards the answer; installing keeps it.

Why not leave it in the drawer record. Because then the drawer is a lie, and
stock stays 1 forever so the minimum-stock alarm never fires -- the fitted one
clogs mid-job and there is no spare. See docs/TRAPS.md.

    itq run scripts/into_service.py --part 213 --tool 474
    itq run scripts/into_service.py --part 213 --tool 474 --commit
    itq run scripts/into_service.py --tool 474 --show

`--show` lists what is currently fitted to a tool, which is the question this
whole mechanism exists to answer.
"""
import argparse
import datetime
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part                       # noqa: E402
from stock.models import StockItem                 # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--part", type=int, help="the consumable's part pk")
ap.add_argument("--tool", type=int, required=True, help="the tool's part pk")
ap.add_argument("--qty", type=float, default=1)
ap.add_argument("--show", action="store_true", help="list what is fitted, then exit")
ap.add_argument("--note", default="")
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

tool = Part.objects.get(pk=a.tool)
tool_stock = tool.stock_items.all()

if tool_stock.count() != 1:
    print(f"!! tool #{tool.pk} {tool.name[:44]} has {tool_stock.count()} stock rows.")
    print("   A tool must be stocked exactly once before anything can be fitted to")
    print("   it — which is a useful forcing function: the FR-301 turned out to")
    print("   have no stock row at all, so the shop's own gun did not physically")
    print("   exist in the data.")
    raise SystemExit(1)
ts = tool_stock.first()

def fitted():
    return list(StockItem.objects.filter(belongs_to=ts).select_related("part"))

print(f"tool  #{tool.pk} {tool.name[:52]}")
print(f"      stock #{ts.pk} @ {ts.location.pathstring if ts.location else '-'}")
print("      fitted now:")
for s in fitted() or []:
    print(f"        stock #{s.pk}  {s.part.name[:50]}  qty={float(s.quantity):g}")
if not fitted():
    print("        (nothing)")

if a.show:
    raise SystemExit

if not a.part:
    print("\n!! --part is required unless --show")
    raise SystemExit(1)

part = Part.objects.get(pk=a.part)
avail = [s for s in part.stock_items.filter(belongs_to__isnull=True)
         if float(s.quantity) > 0]
print(f"\nconsumable #{part.pk} {part.name[:52]}")
print(f"      stock={part.get_stock_count():g}  min={float(part.minimum_stock):g}"
      f"  low={part.is_part_low_on_stock()}")
for s in avail:
    print(f"      available row #{s.pk} qty={float(s.quantity):g} "
          f"@ {s.location.name if s.location else '-'}")

src = next((s for s in avail if float(s.quantity) >= a.qty), None)
if src is None:
    print(f"\n!! no single un-installed row holds {a.qty:g}. Nothing to fit.")
    print("   This is the alarm working: you have no spare.")
    raise SystemExit(1)

whole = abs(float(src.quantity) - a.qty) < 1e-9
print(f"\nplan: {'move the whole row' if whole else f'split {a.qty:g} off'} "
      f"#{src.pk} and set belongs_to=stock #{ts.pk}")

if not a.commit:
    print("\nDRY RUN — add --commit")
    raise SystemExit

today = datetime.date.today().isoformat()
note = (f"IN SERVICE — fitted to {tool.name} (stock #{ts.pk}) on {today}. "
        f"Installed rather than consumed: it is owned and findable, and it is "
        f"not a spare, which is why it no longer counts toward stock. "
        + (a.note or ""))

if whole:
    target = src
else:
    # splitInto leaves the remainder on the original row.
    target = StockItem.objects.create(part=part, location=src.location,
                                      quantity=a.qty, notes=note)
    StockItem.objects.filter(pk=src.pk).update(
        quantity=float(src.quantity) - a.qty)
    left = float(StockItem.objects.get(pk=src.pk).quantity)
    assert abs(left - (float(src.quantity) - a.qty)) < 1e-9, "split did not stick"
    print(f"OK  split: row #{src.pk} now {left:g}, new row #{target.pk} = {a.qty:g}")

StockItem.objects.filter(pk=target.pk).update(belongs_to=ts, notes=note)
chk = StockItem.objects.get(pk=target.pk)
assert chk.belongs_to_id == ts.pk, f"belongs_to did not stick: {chk.belongs_to_id}"
print(f"OK  stock #{chk.pk} installed into #{ts.pk}")

part.refresh_from_db()
low = part.is_part_low_on_stock()
print(f"\n#{part.pk} stock now {part.get_stock_count():g}  min "
      f"{float(part.minimum_stock):g}  low={low}"
      f"{'   <- REORDER: no spare' if low else ''}")
