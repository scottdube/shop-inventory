#!/usr/bin/env python3
"""Catalogue DP-001, the 12 V marine/RV accessory panel.

It has been written up in detail in sln-ha-config §7 since 2026-09-19 —
including the rear-side terminal survey and, today, the rocker's rating — and
has never had an InvenTree record at all. A part that is well documented in a
repo and absent from the catalogue is invisible to every "do we own one?" query,
which is the one question the catalogue exists to answer.

WHY THE DP- PREFIX IS KEPT IN THE NAME. DP-001 is a doc-local designator from
the power-supply inventory, not an InvenTree IPN. Carrying it into the part name
is what lets the doc and the catalogue be read against each other; PS-011 and
POE-001..004 are already named this way and the convention should not fork here.

NO STOCK ROW AND NO LOCATION. Both come from Scott. The doc says only "stored
outside the DC SUPPLIES bin", which is not an address, and a photograph of one
panel is identity, not a count. Same posture as add_s360_psu.py.

WHAT IS AND IS NOT ESTABLISHED, kept separate on purpose:
  measured/read  - rocker 20 A 12 VDC (off the switch body, 2026-09-19)
                 - nine terminals, zero interconnects (rear survey, 2026-09-19)
  estimated      - ~4.3 in square plate (off a mat ruler, with parallax)
  NOT known      - the rocker's 3-blade pinout, the spade sizes, the socket's
                   and USB port's own ratings, where the panel physically is

    itq run scripts/add_dp001_panel.py [--commit]
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory  # noqa: E402
from stock.models import StockItem  # noqa: E402

COMMIT = "--commit" in sys.argv
CATEGORY_PK = 54          # Electronics/Power — where POE-001..004 and PS-011 live
PREFIX = "DP-001 "

NAME = "DP-001 12V Accessory Panel, 4-position"
DESC = ("Marine/RV gasketed 4-hole panel, ~4.3 in square: 12V cigarette socket, "
        "USB charging socket, illuminated rocker 20A 12VDC, digital voltmeter. "
        "Four INDEPENDENT components - no interconnects, no fusing.")
KEYWORDS = ("DP-001 12V accessory panel marine RV boat cigarette lighter socket "
            "USB charging rocker switch illuminated voltmeter gauge 4-position "
            "distribution front panel gasketed weather cap")
NOTES = """**Front panel for the §4 12 V bus** — a Mean Well LRS-350-12 behind it into a fused distribution block gives a bench 12 V supply with switched output, live readout and both socket types. Project hardware awaiting a build, not a supply pulled off a shelf.

Full write-up: `sln-ha-config/docs/reference/power-supply-inventory.md` §7.

    Top left      12 V cigarette socket, weather cap    2 large blade spades, +/-
    Top right     USB charging socket, weather cap      2 large blade spades, +/-
    Bottom left   Illuminated rocker, red LED           3 blades: supply / load / lamp gnd
    Bottom right  Digital voltmeter                     2 small gold spades, +/-

**THERE IS NO TOPOLOGY — NINE TERMINALS, ZERO INTERCONNECTS.** Rear survey 2026-09-19 found no bus bars, no jumpers, no factory wiring between any of the four. They are four independent components sharing a mounting plate. **The rocker gates nothing until it is wired to gate something.** Anyone who assumes the plate is a pre-wired panel will energise the sockets and conclude the switch is faulty.

**NO ONBOARD FUSING ON ANY OF THE FOUR.** Every fuse in the build is one to add:

    +12V -- fuse 20A -- rocker --+-- fuse 15A -- 12V socket
                                 +-- fuse  3A -- USB socket
                                 +------------- voltmeter
    GND -------------------------+-- all negatives

**Rocker: 20 A 12 VDC**, read off the switch body 2026-09-19. This cleared the layout. A 12 V cigarette socket passes 10–15 A, and a 10 A rocker upstream of one *is* the fuse — it welds closed or melts. At 20 A the switch is above the socket's ceiling, so **one rocker carries the whole panel**: no always-hot bypass feed, no relay, no split load. Those fallbacks were contingency for a 10 A part and are withdrawn.

**Main fuse 20 A — not 25 or 30.** Legitimate maximum is 15 A + 3 A + the meter's milliamps ≈ 18 A, and 20 A is the rocker's own ceiling, so one fuse protects the switch and its feed wire together. The branch fuses protect the branches. Reaching for a bigger main because the socket "only" pulls 15 A puts the rocker back in the position of being the fuse.

**240 W through a plastic rocker needs 12 AWG to the switch**, not the 16–18 AWG a 12 V panel invites.

**Putting the voltmeter downstream of the rocker** settles its continuous quiescent draw on any battery-fed install, and gives one kill switch for the whole panel.

**⚠ DO NOT FEED THIS FROM PS-009** (12 V 1.5 A). The 12 V socket alone is rated well beyond that brick. The USB port and meter would be fine; the socket would not.

**Still to establish before wiring — each one is a meter or a caliper, not a search:**
- **The rocker's 3-blade pinout.** Continuity mode. It varies by manufacturer and guessing backfeeds the lamp.
- **Spade sizes, for crimps.** Sockets look like 1/4 in (6.35 mm); the voltmeter's are noticeably smaller, likely 4.8 mm. Both unmeasured.
- **The socket's and USB port's own ratings.** The 10–15 A figure is what sockets of this pattern typically pass, not a reading off this one.
- **Plate size.** ~4.3 in square is off a mat ruler with parallax. **Measure before cutting an opening for it.**

**Possible fuse block already owned:** [#239 WATERWICH 6-Way Blade Fuse Box] is in the catalogue with no stock row — shipped 13 Aug 2018, same era and same project as this panel. Check the parts bins before ordering.

**Quantity and location deliberately unset.** The doc says only "stored outside the DC SUPPLIES bin", which is not an address, and one panel in a photograph is identity, not a count."""


def check():
    lim = (("name", NAME, 100), ("description", DESC, 250), ("keywords", KEYWORDS, 250))
    bad = [f"{f}: {len(v)} > {n}" for f, v, n in lim if len(v) > n]
    for f, v, n in lim:
        print(f"   {f:12s} {len(v):3d}/{n}")
    if bad:
        print("FIELD TOO LONG — full_clean() would abort:", *bad)
        sys.exit(1)


cat = PartCategory.objects.get(pk=CATEGORY_PK)
existing = Part.objects.filter(name__startswith=PREFIX).first()
print(f"category: {cat.pathstring}")
print(f"{NAME}")
check()
print(f"\nexisting: {('#%d' % existing.pk) if existing else 'will create'}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    print("No stock row: count and location come from Scott.")
    sys.exit(0)

if existing is None:
    p = Part.objects.create(name=NAME, description=DESC, category=cat,
                            keywords=KEYWORDS, notes=NOTES, active=True,
                            purchaseable=False, component=True)
else:
    p = existing
    Part.objects.filter(pk=p.pk).update(name=NAME, description=DESC, category=cat,
                                        keywords=KEYWORDS, notes=NOTES)
p.refresh_from_db()

print(f"\n#{p.pk} {p.name}")
print(f"    category        {p.category.pathstring}")
print(f"    rocker rating   {'20 A 12 VDC' in p.notes}")
print(f"    no-topology     {'NINE TERMINALS, ZERO INTERCONNECTS' in p.notes}")
print(f"    PS-009 warning  {'DO NOT FEED THIS FROM PS-009' in p.notes}")
print(f"    fuse-block lead {'#239' in p.notes}")
print(f"    stock rows      {StockItem.objects.filter(part=p).count()}  <- awaiting count + location from Scott")
