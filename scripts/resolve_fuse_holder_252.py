#!/usr/bin/env python3
"""Resolve the fuse holder in the 2026-09-19 relay photo: it is #252.

Scott, 2026-09-19: "its 252 but it isnt part of that purchase. It was in a
sealed bag with the relay, no need to keep that as a package tho".

THREE SEPARATE FACTS IN ONE SENTENCE, and the middle one is the load-bearing
one:

  1. IDENTITY  -> #252, the water-resistant ATC inline holder. No new part.
  2. PROVENANCE-> NOT the 2016-08-23 Amazon 3-pack. It came sealed in a bag
                  with the Boat Command relay [#1233], so it is free stock on
                  the same footing: the boat was sold and the system went with
                  it.
  3. PACKAGING -> do not keep the bag as a unit. Holder and relay are filed
                  apart.

WHY (2) IS THE ONE THAT MATTERS. #252 has carried a purchase-history note
since 2026-08-19 -- one order, a 3-pack, $2.663 each -- and no stock row ever.
The obvious move on finding a physical holder is to put a row on the part and
consider the record closed. That would silently assert that the 2016 purchase
is what was just found. It is not. **The three holders from 2016 remain
unaccounted for**, and a stock row that does not say so converts an open
question into a wrong answer. Same failure mode as reading a pack size off a
used bag, which cost ten keystones earlier today.

NO STOCK ROW HERE. The count comes from Scott, and L2-D2 needs his eye for
space before anything is filed into it -- B3-R6C4 was the right drawer by
every attribute the database holds and was full.

    itq run scripts/resolve_fuse_holder_252.py [--commit]
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
PART_PK = 252
RELAY_PK = 1233
LOC_PK = 592              # resolved below by pathstring, this is a fallback

DESC = ("Water-resistant in-line holder for one standard ATO/ATC blade fuse. "
        "Sealed screw-together barrel on 16 AWG pigtail leads, larger body. "
        "Takes the same blade fuses as #346. Amazon sold it as a 3-pack; "
        "stock counts PIECES, not packs.")

ADD = """

---

## Provenance resolved 2026-09-19 — and it is NOT the 2026 purchase above

Scott, holding it: *"its 252 but it isnt part of that purchase. It was in a sealed bag with the relay, no need to keep that as a package tho."*

**⚠ THE 2016-08-23 3-PACK ABOVE IS STILL UNACCOUNTED FOR.** The holder found today came sealed in a bag with [Relay 40A 12VDC SPDT #1233], which is Boat Command hardware — a different origin entirely. Three holders were bought in 2016 and nobody has seen them. **Any stock row on this part counts what was found today and says nothing about those three.** Do not read a row here as closing the 2016 purchase.

That distinction is the whole reason this note exists. A physical unit turning up for a part whose only history is one purchase order looks exactly like that purchase arriving — and the natural next move, putting a row on the part and moving on, would quietly assert something false.

**FREE STOCK.** Same footing as #1233: the Boat Command system went with the boat when Scott sold it, so nothing can claim this holder back.

**DO NOT KEEP THE BAG AS A UNIT.** Scott: *"no need to keep that as a package."* The holder and the relay are filed apart, each under its own part. This is deliberately **not** the assortment-kit case in `TECHNIQUES.md` where a box becomes a LOCATION — that applies when the contents are only findable as a set, and two items of different families is not a set.

**It is the right holder for the DP-001 build.** [DP-001 #1232] needs 20 A / 15 A / 3 A ATO/ATC blade fusing, and [#346 Fuse Kit, ATO/ATC blade, 120 pc] in `L2-D2` holds all three values. Holder, fuses and relay are all on hand.

**NOT the same family as [#1203 Fuse Holder, inline 5x20 mm]** — that one is a glass cartridge holder and was ruled out by inspection, not by guess.

**Count and location still open.** Nobody has counted what is in hand, and `L2-D2` is the proposed home (it holds #346 and #1203) but has not been checked for space."""

RELAY_OLD = "**Related, possibly already owned:** an inline ATC/ATO blade fuse holder was in the same photo. [#252 Water-resistant ATC Fuse Holder, 16 Gauge In-Line] is in the catalogue as a 2016 3-pack with **no stock row** — very likely the same item. Count what is actually on hand and fill that row rather than creating a second part."

RELAY_NEW = "**RESOLVED 2026-09-19 — the inline fuse holder in the same photo is [#252 Water-resistant ATC Fuse Holder, 16 Gauge In-Line].** Scott identified it and added the part that a photo could never show: *it is not from #252's 2016 purchase.* It was sealed in a bag with this relay, so it is Boat Command hardware and free stock on the same footing. **The 2016 3-pack remains unaccounted for.** The bag is not kept as a unit — Scott: *\"no need to keep that as a package\"* — so holder and relay are filed apart."

p = Part.objects.get(pk=PART_PK)
relay = Part.objects.get(pk=RELAY_PK)
loc = StockLocation.objects.filter(pathstring__endswith="L2/L2-D2").first()

print(f"#{p.pk} {p.name}")
print(f"  desc now  {p.description[:90]}")
print(f"  desc new  {len(DESC)}/250")
print(f"  rows      {StockItem.objects.filter(part=p).count()}")
print(f"  proposed default_location  [{loc.pk}] {loc.pathstring}"
      f"  ({StockItem.objects.filter(location=loc).count()} rows)")
print(f"  relay anchor found: {RELAY_OLD in relay.notes}")
print(f"  already applied:    {'Provenance resolved 2026-09-19' in (p.notes or '')}")
if len(DESC) > 250:
    print("\nDESCRIPTION TOO LONG."); sys.exit(1)
if RELAY_OLD not in relay.notes:
    print("\nRELAY ANCHOR NOT FOUND — refusing a half edit."); sys.exit(1)

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    print("NO stock row will be created: count comes from Scott.")
    sys.exit(0)

Part.objects.filter(pk=p.pk).update(description=DESC, default_location=loc,
                                    notes=(p.notes or "") + ADD)
Part.objects.filter(pk=relay.pk).update(notes=relay.notes.replace(RELAY_OLD, RELAY_NEW))
p.refresh_from_db(); relay.refresh_from_db()

print(f"\n#{p.pk} {p.name}")
print(f"    description      {p.description[:80]}...")
print(f"    default_location {p.default_location.pathstring}")
print(f"    2016 flagged     {'THE 2016-08-23 3-PACK ABOVE IS STILL UNACCOUNTED FOR' in p.notes}")
print(f"    free stock       {'FREE STOCK' in p.notes}")
print(f"    no-package       {'DO NOT KEEP THE BAG AS A UNIT' in p.notes}")
print(f"    #1203 ruled out  {'#1203' in p.notes}")
print(f"    stock rows       {StockItem.objects.filter(part=p).count()}  <- awaiting count from Scott")
print(f"\n#{relay.pk} lead updated")
print(f"    resolved         {'RESOLVED 2026-09-19' in relay.notes}")
print(f"    old guess gone   {RELAY_OLD not in relay.notes}")
