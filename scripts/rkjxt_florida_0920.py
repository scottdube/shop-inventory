#!/usr/bin/env python3
"""Split the surviving RKJXT nav switch to Florida Staging for the PFD.

Scott, 2026-09-20: "There were two purchased. One is in the MFD that's sitting
in the simulator now, part of the G1000 build. And the other is sitting staged
to go to Florida to be put into the PFD when the second G1000 is built."

Both units are therefore ACCOUNTED FOR, and neither is loose stock:

  unit 1  soldered into the MFD, in the simulator at SLN -> allocated to
          BO-0020 (Sim G1000 MFD), consumed when that build closes
  unit 2  in the Florida bag, earmarked for the PFD on G1000 build #3

SPLIT RATHER THAN MOVE, because the two units are in different places and one
of them is spoken for. Moving the whole row would carry the MFD's switch to
Florida on paper while it sits soldered into a panel in New Hampshire. The
"one row per part per location" invariant explicitly allows a split for a
different location, and this is that case.

The split takes from the UNALLOCATED unit: the source row keeps its BO-0020
allocation. The verify block below refuses anything else.

THE SOURCE EARMARK IS CLEARED. Row 9 already carried a florida tag and
metadata reading "FIND IT, it is in Unfiled not a real place" -- placed today,
before the MC-T3 count answered it. That earmark is now embodied in the new
Florida row; leaving it on the source would count the same switch twice, which
is the trap split_330_470_0920.py hit on row 125 this morning. It is also now
simply false: what stays on row 9 is the MFD's switch, which is not going to
Florida at all.

    itq run scripts/rkjxt_florida_0920.py
    itq run scripts/rkjxt_florida_0920.py --commit
"""
import os
import sys
from datetime import date

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
user = get_user_model().objects.filter(is_superuser=True).first()

SRC_PK = 9
TAKE = 1
BAG = StockLocation.objects.get(pk=503)
BATCH = "G1000 PFD build #3"

src = StockItem.objects.get(pk=SRC_PK)
print(f"source row {SRC_PK} [#{src.part.pk}] {src.part.name}")
print(f"  qty={src.quantity} available={src.quantity - src.allocation_count()} "
      f"allocated={src.allocation_count()} loc={src.location.name}")
print(f"  tags={[t.name for t in src.tags.all()]} meta={src.metadata}")
print(f"  taking {TAKE} -> {BAG.pathstring}, leaving {src.quantity - TAKE} (the allocated MFD unit)")

if src.quantity - src.allocation_count() < TAKE:
    print("*** REFUSING: not enough UNALLOCATED stock to split ***")
    sys.exit(1)

if not COMMIT:
    print("\nDRY RUN - rerun with --commit")
    sys.exit(0)

new = src.splitStock(TAKE, location=BAG, user=user)
new.batch = BATCH
new.metadata = {"florida": {
    "qty": float(TAKE),
    "why": "G1000 build #3 (PFD) at LRD - BO-0017 - the 4-direction nav switch",
    "added": str(date.today())}}
new.notes = """Split from row 9 on 2026-09-20 for the Florida bag.

FOR THE PFD ON G1000 BUILD #3. Scott: "the other is sitting staged to go to
Florida to be put into the PFD when the second G1000 is built."

THIS IS THE LAST ONE. Two were bought on Mouser order 29983486 (2023-09-04);
the other is soldered into the MFD now sitting in the simulator at SLN and is
allocated to BO-0020. There is no third, and no spare -- a second one means a
new Mouser order with whatever lead time Alps has that week.

COUNT IS REAL. Tallied by Scott 2026-09-20 with the MC-T3 drawer open. This
row does not inherit an estimate.

It reached the Florida bag late: the row was recorded at #502, the waiting
room, not at MC-T3, so the sweep that emptied that drawer today did not see
it. See docs/TRAPS.md, "A location sweep moves rows that SAY the location"."""
new.save()
new.tags.add("florida")

src = StockItem.objects.get(pk=SRC_PK)
src.notes = (src.notes or "") + f"""

2026-09-20: {TAKE} split out to Florida Staging (row {new.pk}) for the PFD on
G1000 build #3. What remains on THIS row is the MFD's switch -- soldered into
the panel in the simulator at SLN and allocated to BO-0020, not stock anyone
can pick. The row reads 1 until that build closes and consumes it.

The florida earmark that stood on this row ("FIND IT, it is in Unfiled not a
real place") is CLEARED: the count found it, and the travelling unit is now
row {new.pk}. What is left here is not going to Florida."""
src.metadata = {}
src.save()
src.tags.remove("florida")

# Verify. .save() on this install has reported success and written nothing.
s = StockItem.objects.get(pk=SRC_PK)
n = StockItem.objects.get(pk=new.pk)
print(f"\nAFTER {SRC_PK}: qty={s.quantity} allocated={s.allocation_count()} loc={s.location.name}")
print(f"AFTER {n.pk}: qty={n.quantity} loc={n.location.pathstring} batch={n.batch!r} "
      f"tags={[t.name for t in n.tags.all()]} florida={(n.metadata or {}).get('florida', {}).get('qty')}")

src_tags = [t.name for t in s.tags.all()]
print(f"           src tags={src_tags} src meta={s.metadata}")
ok = (n.location_id == BAG.pk and n.quantity == TAKE and n.batch == BATCH
      and "florida" in [t.name for t in n.tags.all()]
      and s.quantity == 1 and s.allocation_count() == 1
      and "florida" not in src_tags and not (s.metadata or {}))
print("VERIFIED" if ok else "*** VERIFY FAILED ***")
sys.exit(0 if ok else 1)
