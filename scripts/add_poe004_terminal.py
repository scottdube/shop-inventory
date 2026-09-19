#!/usr/bin/env python3
"""Terminal unit + 48 V adapter located. Catalogue both, and withdraw the
SURPLUS verdict on #1223.

Scott, 2026-09-19: "I just located one of the uh, one of the terminal units so
at the endpoint for the D-Link and so I have at least one of those and I have a
power supply for one of those I got to see if I can find the other power supply
in the other other terminal unit."

WHY THE VERDICT CHANGES, AND WHY THAT IS NOT THE SAME AS BEING WRONG. #1223 was
called SURPLUS because the step-down existed nowhere in the building, which was
true of the evidence at the time. A terminal unit has now been found, so the
premise is gone. The ADVICE attached to it -- do not BUY a terminal unit -- was
correct and stands; Scott did not buy one, he found one.

And the kit is no longer redundant with POE-001, for one specific reason:
POE-001 is 5 V only. The terminal unit does 12 V. Delivering 12 V over an
Ethernet run is a capability nothing else on this shelf has.

Quantities are CONFIRMED FLOORS, not counts. Scott said "at least one" of each
and is still searching for a possible second of both.

    itq run scripts/add_poe004_terminal.py [--commit]
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
CATEGORY_PK, BIN_PK = 54, 617
POE003, POE001 = 1223, 1222

TERM_NAME = "POE-004 PoE Terminal Unit 5V/12V, 10/100"
TERM_DESC = ("D-Link DWL-P200 terminal unit (endpoint half of the kit). Takes 48V "
             "off pins 4/5+7/8, outputs 5V 2.5A OR 12V 1A on a DC barrel, selected "
             "by DIP switch. 10/100 only. Pairs with POE-003.")
TERM_KEYWORDS = ("POE-004 D-Link DLink DWL-P200 DWLP200 PoE terminal unit endpoint "
                 "splitter passive 5V 12V DIP 10/100 power over ethernet")
TERM_NOTES = """D-Link **DWL-P200 terminal unit** — the ENDPOINT half of the two-piece passive PoE kit. Located 2026-09-19.

    Input    48 VDC off the spare pairs (4/5, 7/8) from a POE-003 base unit
    Output   **5 V @ 2.5 A  OR  12 V @ 1 A** — selected by a **DIP SWITCH**
    LAN      RJ-45, 10/100 Mbps only
    Pairs with  [POE-003 #1223], and with nothing else on site

**⚠ CHECK THE DIP SWITCH BEFORE CONNECTING A LOAD, EVERY TIME.** The two settings share one barrel jack and nothing about the connector tells you which is selected. A 12 V device on the 5 V setting simply will not run, which is the harmless direction and the one that gets misdiagnosed. **A 5 V device on the 12 V setting dies.** The switch position is not recorded here on purpose — read it off the unit, do not trust a record of it.

**THIS IS THE ONLY WAY SLN CAN PUT 12 V ON AN ETHERNET RUN.** That is the reason to keep the kit. [POE-001 #1222] is the better part for almost everything — active 802.3af/at, gigabit, isolated, straight off the installed `USW` ports — but it is **5 V only**. For a 12 V device at the end of a cable run, this kit is the only option in the building.

**Use it as a MATCHED PAIR and nothing else:**
- **Never plug a POE-003 base unit into a `USW Lite 16 PoE` or `USW 24 PoE` port.** It is passive and injects its own 48 V; the switch port is a PSE. Do not connect two power sources to each other.
- **Never feed an 802.3af/at device from POE-003.** It cannot negotiate, so the device will not take power from it.
- **Never substitute POE-002 for this unit.** POE-002 passes the 48 V straight through with no step-down — measured on the bench 2026-09-19. This terminal unit is the step-down. That is the entire difference between them, and they do not look different.

**Its 48 V supply is [PS-011].** 10/100 only, so putting this kit in a run caps that link at 100 Mbit regardless of the gear at either end.

**Quantity is a confirmed floor, not a count.** Scott has *"at least one"* and is still searching for a possible second. Bump the row when the search finishes."""

PSU_NAME = "PS-011 Power Adapter 48V 0.4A, for DWL-P200"
PSU_DESC = ("Mains adapter for the D-Link DWL-P200 PoE base unit. 100-240VAC in, "
            "48VDC 400mA out. Barrel size NOT recorded - measure it. This is the "
            "only 48V supply known on site.")
PSU_KEYWORDS = ("PS-011 48V 0.4A 400mA power supply adapter brick D-Link DWL-P200 "
                "PoE injector mains")
PSU_NOTES = """Mains adapter for the [POE-003 #1223] D-Link DWL-P200 base unit. Located 2026-09-19.

    Input   100-240 VAC, 50/60 Hz
    Output  **48 VDC, 400 mA**   (per the DWL-P200 datasheet)

**48 V IS THE ODD ONE OUT IN THIS SHOP AND THAT IS THE HAZARD.** Bin B-02 is otherwise 12 V and 24 V bricks, and a 48 V supply with a barrel plug that fits them is a way to destroy something quietly. It exists to feed a PoE base unit and nothing else.

**The barrel size and polarity are NOT recorded — measure them before this is filed next to the 12 V and 24 V bricks.** If it physically mates with the 12 V gear in the same bin, that is worth knowing and worth separating.

**This supply is why an earlier "no 48 V supply on site" note was retracted.** An inventory sweep for 48 V returned nothing and that silence was written up as a fact about the shop; Scott then powered a base unit, which proved a 48 V source existed. The catalogue had a hole, the shop did not. This record closes it.

**Quantity is a confirmed floor, not a count.** Scott has one and is still looking for a second."""

OLD_VERDICT_HEAD = "**VERDICT: SURPLUS. Do not buy the missing pieces.**"
NEW_VERDICT = """**VERDICT REVISED 2026-09-19: KEEP as a matched pair. (Was SURPLUS — premise withdrawn, not the reasoning.)**

A **terminal unit has been located** ([POE-004]), along with its 48 V adapter ([PS-011]). SURPLUS rested on the step-down existing nowhere in the building, and that is no longer true. The *advice* attached to it — do not BUY a terminal unit — was right and stands; one was found, not bought.

**What the complete kit is worth keeping for: 12 V over an Ethernet run.** [POE-001 #1222] beats it on everything else and needs no injector at all, but POE-001 is **5 V only**. The DWL-P200 terminal unit does **12 V @ 1 A**, and nothing else on this shelf delivers 12 V down a cable run. That is the whole case for the kit, and it is a real one.

**Do not buy a second terminal unit** if the search for one comes up empty. One complete pair covers the capability; a second adds nothing at 10/100.

**Superseded note, kept for the reasoning:** this part was briefly recorded as surplus on the grounds that completing the kit meant buying a discontinued part to get 5 V/12 V over a 10/100 link from a device that cannot negotiate. That arithmetic is still correct for BUYING one. It was never an argument for throwing away one you already have."""


def check(name, desc, kw):
    lim = {"name": (name, 100), "description": (desc, 250), "keywords": (kw, 250)}
    bad = [f"{f}: {len(v)} > {n}" for f, (v, n) in lim.items() if len(v) > n]
    for f, (v, n) in lim.items():
        print(f"   {f:12s} {len(v):3d}/{n}")
    if bad:
        print("FIELD TOO LONG — full_clean() would abort:", *bad)
        sys.exit(1)


cat = PartCategory.objects.get(pk=CATEGORY_PK)
loc = StockLocation.objects.get(pk=BIN_PK)
print(f"category: {cat.pathstring}\nbin:      {loc.pathstring}\n")
for nm, d, k in ((TERM_NAME, TERM_DESC, TERM_KEYWORDS), (PSU_NAME, PSU_DESC, PSU_KEYWORDS)):
    print(nm)
    check(nm, d, k)

p3 = Part.objects.get(pk=POE003)
if OLD_VERDICT_HEAD not in p3.notes:
    print("\n#1223 verdict anchor MISSING — aborting rather than writing a half edit")
    sys.exit(1)
print("\n#1223 verdict anchor found; SURPLUS will be replaced with the revised verdict")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)


def upsert(prefix, name, desc, kw, notes, qty):
    ex = Part.objects.filter(name__startswith=prefix).first()
    if ex is None:
        p = Part.objects.create(name=name, description=desc, category=cat,
                                keywords=kw, notes=notes, default_location=loc,
                                active=True, purchaseable=True, component=True)
    else:
        p = ex
        Part.objects.filter(pk=p.pk).update(name=name, description=desc, category=cat,
                                            keywords=kw, notes=notes, default_location=loc)
    p.refresh_from_db()
    si = StockItem.objects.filter(part=p, location=loc).first()
    if si is None:
        si = StockItem.objects.create(part=p, location=loc, quantity=qty)
    si.refresh_from_db()
    return p, si


term, term_si = upsert("POE-004 ", TERM_NAME, TERM_DESC, TERM_KEYWORDS, TERM_NOTES, 1)
psu, psu_si = upsert("PS-011 ", PSU_NAME, PSU_DESC, PSU_KEYWORDS, PSU_NOTES, 1)

# Resolve the placeholders now that the pks exist.
for p in (term, psu, Part.objects.get(pk=POE003)):
    n = p.notes.replace("[POE-004]", f"[POE-004 #{term.pk}]").replace("[PS-011]", f"[PS-011 #{psu.pk}]")
    if n != p.notes:
        Part.objects.filter(pk=p.pk).update(notes=n)

p3 = Part.objects.get(pk=POE003)
i = p3.notes.index(OLD_VERDICT_HEAD)
j = p3.notes.index("\n\n", p3.notes.index("Kept rather than discarded", i))
revised = (p3.notes[:i] + NEW_VERDICT + p3.notes[j:]).replace(
    "[POE-004]", f"[POE-004 #{term.pk}]").replace("[PS-011]", f"[PS-011 #{psu.pk}]")
Part.objects.filter(pk=POE003).update(notes=revised)
p3.refresh_from_db()

for p, si in ((term, term_si), (psu, psu_si)):
    print(f"\n#{p.pk} {p.name}")
    print(f"    category         {p.category.pathstring}")
    print(f"    default_location {p.default_location.pathstring}")
    print(f"    stock [{si.pk}] qty {si.quantity:g} @ {si.location.pathstring}")
print(f"\n#1223 SURPLUS withdrawn:      {'VERDICT: SURPLUS' not in p3.notes}")
print(f"#1223 revised verdict present: {'KEEP as a matched pair' in p3.notes}")
print(f"#1223 48V hazard still present:{'MEASURED, NOT PREDICTED' in p3.notes}")
print(f"#1223 links resolved:          {('#%d' % term.pk) in p3.notes and ('#%d' % psu.pk) in p3.notes}")
print(f"POE-004 DIP warning present:   {'CHECK THE DIP SWITCH' in term.notes}")
