"""Decision queue items 1, 2 and 4, approved by Scott 2026-08-24.

Item 3 (#354 wrist BP monitor) is deliberately absent: it is ALREADY
active=False. The queue entry claiming it was still live was stale. Verified,
not assumed - see the assertion below, which fails loudly if that changes.

MERGE DIRECTION. Both losers (#94, #90) have zero SupplierParts and zero stock
rows, so nothing has to be carried across and neither merge can lose data.

  #94  -> #107   #107 holds the SupplierPart (Mouser 841-MPXV6115VC6U), the
                 IPN and the one stock row. #94 is an empty purchase-history
                 shell.
  #90  -> #142   Less obvious. #90 has the better NAME and the right CATEGORY
                 (Equipment/Soldering - a hot plate is durable equipment, not a
                 consumable). #142 has the SupplierPart, the ASIN and a proper
                 `orig:` description. Data beats presentation: #142 survives,
                 and this script fixes what #90 was right about by moving #142
                 to Equipment/Soldering and giving it a canonical name. Merging
                 the other way would mean re-creating a SupplierPart, which is
                 how duplicates get made rather than removed.

Tombstones follow the #54 pattern exactly: kept, not deleted; active=False;
name suffixed " [merged]"; description states where it went.

Every write is re-read and asserted, per the silent-save trap: .save() can
report success and write nothing.
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory          # noqa: E402
from stock.models import StockItem                  # noqa: E402

import argparse                                     # noqa: E402
ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()
DRY = not a.commit


def tombstone(loser_pk, winner_pk):
    loser = Part.objects.get(pk=loser_pk)
    winner = Part.objects.get(pk=winner_pk)
    assert loser.supplier_parts.count() == 0, f"#{loser_pk} has suppliers - would lose data"
    assert StockItem.objects.filter(part=loser).count() == 0, f"#{loser_pk} has stock - would lose data"
    if not loser.active and "[merged]" in loser.name:
        print(f"  SKIP #{loser_pk}: already a tombstone")
        return
    new_name = f"{loser.name} [merged]"[:200]
    new_desc = f"MERGED into part #{winner.pk} ({winner.name[:60]})."[:250]
    print(f"  #{loser_pk} {loser.name[:45]!r} -> tombstone pointing at #{winner_pk}")
    if DRY:
        return
    Part.objects.filter(pk=loser_pk).update(name=new_name, description=new_desc, active=False)
    fresh = Part.objects.get(pk=loser_pk)
    assert fresh.active is False and "[merged]" in fresh.name, "tombstone write did not stick"
    print(f"    + ok: active={fresh.active} name={fresh.name[:55]!r}")


print("=== item 3 precondition: #354 must already be inactive ===")
p354 = Part.objects.get(pk=354)
assert p354.active is False, "#354 is ACTIVE - the queue entry was right after all, stop and re-decide"
print(f"  #354 active={p354.active} - confirmed, nothing to do\n")

print("=== item 1: pressure sensor #94 -> #107 ===")
tombstone(94, 107)

print("\n=== item 2: hot plate #90 -> #142 ===")
tombstone(90, 142)

CANON = "Soldering Hot Plate, 110V 360W, 30-400C, digital"
equip = PartCategory.objects.filter(name="Soldering", parent__name="Equipment").first() \
    or Part.objects.get(pk=90).category
p142 = Part.objects.get(pk=142)
print(f"  #142 recategorise {p142.category} -> {equip}")
print(f"  #142 rename {p142.name[:50]!r} -> {CANON!r}")
if not DRY:
    Part.objects.filter(pk=142).update(name=CANON, category=equip)
    fresh = Part.objects.get(pk=142)
    assert fresh.name == CANON and fresh.category == equip, "part 142 write did not stick"
    print(f"    + ok: {fresh.name!r} in {fresh.category}")

print("\n=== item 4: clear stocktake stamps that were never counts ===")
for pk in (482, 556):
    s = StockItem.objects.get(pk=pk)
    assert (s.notes or "").startswith("[ESTIMATE]"), \
        f"stock #{pk} notes no longer start with [ESTIMATE] - re-check before clearing"
    print(f"  stock #{pk} part=#{s.part.pk} stocktake={s.stocktake_date} -> None")
    if DRY:
        continue
    StockItem.objects.filter(pk=pk).update(stocktake_date=None)
    fresh = StockItem.objects.get(pk=pk)
    assert fresh.stocktake_date is None, f"stock #{pk} stocktake_date did not clear"
    print(f"    + ok: stocktake_date={fresh.stocktake_date}")

s504 = StockItem.objects.get(pk=504)
print(f"  stock #504 untouched (genuine count, stocktake={s504.stocktake_date})")
print("\nDRY RUN - nothing written" if DRY else "\ncommitted")
