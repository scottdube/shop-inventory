#!/usr/bin/env python3
"""Catalogue POE-003, the D-Link DWL-P200 PoE injector base units. Qty 2.

Files with POE-001 (#1222) in Electronics/Power and bin B-02, same reasoning:
a power-delivery device that happens to arrive over Ethernet belongs on the
shelf that answers "what can power this?".

THE REASON THIS RECORD EXISTS IS THE 48 V, NOT THE INVENTORY LINE. Scott also
has POE-002, an unregulated passive splitter, in the same bin. Base unit +
POE-002 puts 48 V on a 12 V barrel. Both halves look plug-compatible. The
warning goes in the notes of BOTH parts, because whichever one someone picks up
first is the one that has to stop them.

Specs verified against the D-Link datasheet 2026-09-19, not recalled.

    itq run scripts/add_poe003_dlink.py
    itq run scripts/add_poe003_dlink.py --commit
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv

CATEGORY_PK = 54          # Electronics/Power
BIN_PK = 617              # SLN/Storage/WS2/WS2-S3/B-02
POE001_PK = 1222

NAME = "POE-003 PoE Injector 48V passive, 10/100"
DESC = ("D-Link DWL-P200 base unit (injector half of the kit). Puts 48VDC on "
        "pins 4/5 + 7/8 of the spare pairs. 10/100 only. Needs its 48V 400mA "
        "mains adapter. PASSIVE - will not power an 802.3af/at device.")
KEYWORDS = ("POE-003 D-Link DLink DWL-P200 DWLP200 PoE injector base unit passive "
            "48V spare pairs 10/100 power over ethernet")
QTY = 2     # Scott, 2026-09-19: "I have two of these"

NOTES = """D-Link **DWL-P200 base unit** — the INJECTOR half of a two-piece passive PoE kit. Qty 2 (Scott, 2026-09-19: *"I have two of these"*).

Specs verified against the D-Link datasheet on 2026-09-19, not recalled:

    Base unit      inserts DC on the UNUSED pairs — pins 4, 5, 7, 8
    Mains adapter  100-240VAC in, **48VDC 400mA out**
    Terminal unit  splits data/power back apart, steps down to 5V or 12V
                   (DIP-selectable: 5V @ 2.5A, or 12V @ 1A)
    LAN            RJ-45, **10/100 Mbps only** — not gigabit
    Reach          100 m / 328 ft

**⚠ DO NOT PAIR WITH POE-002. IT WILL PUT 48 V ON A 12 V BARREL.**

POE-002 (in this same bin, B-02) is an unregulated passive splitter: it hands the spare pairs straight through to its barrel jack with nothing in between. The DWL-P200's step-down to 5V/12V lives in the **TERMINAL UNIT**, not in the base unit and not in the cable. So base unit + POE-002 = 48 V arriving at a barrel that fits any 12 V device in the shop. The two look plug-compatible and are not. This is the whole reason POE-002 was left uncatalogued rather than filed as a usable part.

**The safe partner is the kit's own terminal unit.** Whether SLN has one has NOT been established — the terminal unit is the SAME HOUSING with a different label, so "two of these" could be two base units or a base plus a terminal. **Read the labels before assuming the kit is complete.** Two base units and no terminal unit is two injectors and no way to use them.

**PASSIVE, so it does not interoperate with the SLN switches.** `USW Lite 16 PoE` and `USW 24 PoE` (SLN ADR-002) are 802.3af/at; they negotiate. This injector does not, and an 802.3af device will not accept power from it. Its use case is the reverse: feeding a NON-PoE device over a cable run, using its own mains adapter — and that only works with a matching step-down terminal unit at the far end.

**10/100 only.** Putting one of these in a run caps that link at 100 Mbit even if both ends are gigabit.

Related: [POE-001 #1222] — the ACTIVE 802.3af/at splitter, which is the part that actually works on the SLN switches. Full write-up in sln-ha-config docs/reference/power-supply-inventory.md section 8."""


def check_limits():
    lim = {"name": (NAME, 100), "description": (DESC, 250), "keywords": (KEYWORDS, 250)}
    bad = [f"{f}: {len(v)} > {n}" for f, (v, n) in lim.items() if len(v) > n]
    if bad:
        print("FIELD TOO LONG — Part.save() calls full_clean(), this would abort:")
        for b in bad:
            print("   ", b)
        sys.exit(1)
    for f, (v, n) in lim.items():
        print(f"   {f:12s} {len(v):3d}/{n}")


cat = PartCategory.objects.get(pk=CATEGORY_PK)
loc = StockLocation.objects.get(pk=BIN_PK)
print(f"category: {cat.pathstring}")
print(f"bin:      {loc.pathstring}")
print(f"qty:      {QTY}   (stated by Scott, not counted from a photo)")
check_limits()

existing = Part.objects.filter(name__startswith="POE-003 ").first()
print(f"part:     {'EXISTS #%d' % existing.pk if existing else 'will create'}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

if existing is None:
    p = Part.objects.create(
        name=NAME, description=DESC, category=cat, keywords=KEYWORDS,
        notes=NOTES, default_location=loc,
        active=True, purchaseable=True, component=True)
else:
    p = existing
    Part.objects.filter(pk=p.pk).update(
        name=NAME, description=DESC, category=cat, keywords=KEYWORDS,
        notes=NOTES, default_location=loc)
p.refresh_from_db()

si = StockItem.objects.filter(part=p, location=loc).first()
if si is None:
    si = StockItem.objects.create(part=p, location=loc, quantity=QTY)
elif si.quantity != QTY:
    StockItem.objects.filter(pk=si.pk).update(quantity=QTY)
si.refresh_from_db()

# The 48V warning has to be on whichever part gets picked up first. POE-001 is
# the other PoE part in this bin and the one that DOES work on the switches, so
# it is the likeliest thing someone reaches for.
poe1 = Part.objects.get(pk=POE001_PK)
marker = "DO NOT PAIR POE-002 WITH POE-003"
if marker not in (poe1.notes or ""):
    add = f"""

**⚠ {marker} (#{p.pk}, D-Link DWL-P200 base unit, same bin).** That injector puts **48 VDC** on the spare pairs, and POE-002 is an unregulated passive splitter that passes them straight to its barrel — 48 V into a 12 V device. The DWL-P200's step-down lives in its TERMINAL unit, which may not be on site. This part (POE-001) is unaffected: it is active, negotiates, and is the one that works on the SLN switches."""
    Part.objects.filter(pk=POE001_PK).update(notes=(poe1.notes or "") + add)
poe1.refresh_from_db()

print(f"\n#{p.pk} {p.name}")
print(f"    category         {p.category.pathstring}")
print(f"    default_location {p.default_location.pathstring}")
print(f"    48V warning present:        {'48 V ON A 12 V BARREL' in p.notes}")
print(f"    terminal-unit check present:{'SAME HOUSING with a different label' in p.notes}")
print(f"    stock [{si.pk}] qty {si.quantity:g} @ {si.location.pathstring}")
print(f"\ncross-warning written into #{POE001_PK}: {marker in poe1.notes}")
