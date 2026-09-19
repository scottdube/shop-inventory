#!/usr/bin/env python3
"""Catalogue the 20A thermal breaker and the TB-1503 that closes the Glarks kit.

Both landed on the bench together 2026-09-19 and both belong in B0-R2C3, but
they are unrelated items and only one of them is new to the shop.

THE TB-1503 IS NOT SALVAGE AND NOT NEW STOCK -- it is the missing 8th member of
kit #283, and the catalogue is what proves it rather than anyone's memory. That
kit (Glarks 124pc, ASIN B07Y21W11W, bought 2022-08-12) was dissolved into
per-component parts on 2026-09-16 into 3/4/5/6/7/8/10/12 positions. Seven of the
eight exist as #1204-#1210 in B0-R2C3. The 3-position had no record because it
was not in the box at dissolution time -- it was already out, wired up. The
moulding reads TB-1503, the rating and clear-cover format match its siblings
exactly, and the jumper fitted to it is #1212 from the same kit.

WHAT IT WAS WIRED INTO IS NOT ESTABLISHED, and nothing here guesses. Observed
2026-09-19: a pre-insulated jumper bridging 1-2-3 and a stranded conductor with
a translucent end cap under screw 1. That is evidence of use and nothing more.

THE BREAKER'S 50 Vdc CEILING IS THE SPEC THAT DECIDES WHERE IT CAN GO, and it
is the one people skip because "20A" is the number printed largest. It suits a
12 or 24 V bus. It must NOT go on the R48 rectifier bus in shrink-fit (#1104,
53.5 V) -- that is over the DC rating, and a DC arc that a breaker cannot clear
does not self-extinguish the way an AC one does at the zero crossing.

AND IT OUT-RATES EVERY BARRIER STRIP IN THE SAME DRAWER. 20 A upstream of a
600V 15A block makes the block the weak link: it can cook while the breaker
sits below its trip point. Protection is sized to the smallest thing
downstream, not to the supply.

    itq run scripts/add_breaker_tb1503.py
    itq run scripts/add_breaker_tb1503.py --commit
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from part.models import Part, PartCategory      # noqa: E402
from stock.models import StockItem, StockLocation  # noqa: E402

COMMIT = "--commit" in sys.argv
HOME = "SLN/Bin Wall/B0/B0-R2C3"

ITEMS = [
    {
        "name": "Barrier Terminal Block, 3-position, 600V 15A, dual row (WEIDU TB-1503)",
        "category": "Connectors",
        "description": (
            "Chassis-mount barrier terminal block, 3 positions, dual row screw, 600 V 15 A, "
            "clear cover, numbered legend. Body marked WEIDU TB-1503. The 3-position member "
            "of Glarks kit #283."),
        "keywords": (
            "barrier terminal block, terminal strip, 3 position, 600V 15A, dual row, "
            "screw terminal, WEIDU, TB-1503, chassis mount, glarks"),
        "notes": """Barrier-style terminal block: two rows of screw terminals bridged in pairs, under a clear insulating cover, with a numbered legend. Body marked **WEIDU TB-1503**, rated **600 V 15 A**.

**THIS IS THE MISSING 8TH MEMBER OF KIT #283**, not a salvaged part and not a new purchase. The Glarks 124-piece kit (ASIN B07Y21W11W, bought 2022-08-12) was dissolved into per-component parts on 2026-09-16 and contains eight strips: 3, 4, 5, 6, 7, 8, 10 and 12 positions. Seven of them became #1204-#1210. The 3-position got no record because it was not in the box -- it was already out and in use somewhere. Identified 2026-09-19 off the moulding, with the rating, the dual-row format and the clear cover all matching its siblings.

**WHAT IT WAS WIRED INTO IS NOT KNOWN.** As found 2026-09-19 it carried a pre-insulated jumper (#1212, from the same kit) bridging positions 1-2-3, and a stranded conductor with a translucent end cap under screw 1. Stripped before filing, so the jumper returns to #1212's pool. Scott, asked directly: *"I don't know if it was salvaged or it was new and just didn't get used."* Left open on purpose -- a plausible story written down here would read as fact in six months.

**NOT interchangeable with the PCB terminal blocks in A3-R8C6/C7.** Those are 2.54 mm and 5.08 mm blocks that SOLDER INTO A BOARD. These are chassis-mount barrier strips that take ring or fork terminals under a screw.

**15 A is the ceiling, and the drawer now also holds a 20 A breaker (#BRK).** Do not let that breaker protect this strip -- see its notes.""",
    },
    {
        "name": "Thermal Circuit Breaker, 20A push-button reset, panel mount (mxuteuk L1-ls-20A)",
        "category": "Electronics/Protection",
        "description": (
            "Panel-mount thermal circuit breaker, 20 A, manual push-button reset, screw "
            "terminals, 125/250 Vac 50 Vdc. mxuteuk L1 series, with waterproof button cap. "
            "UL/cUL, CCC, TUV, RoHS."),
        "keywords": (
            "thermal circuit breaker, overload protector, 20A, push button reset, panel "
            "mount, resettable, mxuteuk, L1 series, L1-ls-20A, 50Vdc, waterproof cap"),
        "notes": """Panel-mount **thermal** circuit breaker with manual push-button reset. Body markings, read 2026-09-19:

    L1 Series   20A   125/250Vac  50Vdc
    UL/cUL, CCC, TUV, RoHS

Threaded bushing with knurled nut for a panel cutout, two screw terminals, and a clear screw-on waterproof button cap (a spare cap came in the bag).

**50 Vdc IS THE RATING THAT DECIDES WHERE THIS CAN GO,** and it is the one that gets skipped because "20A" is printed largest. Fine on a 12 V or 24 V bus. **NOT for the R48 rectifier bus in shrink-fit (#1104, 53.5 V)** -- that is over the DC rating. DC matters more than the AC number suggests: an AC arc self-extinguishes at every zero crossing and a DC arc does not, which is why the same contacts are rated 250 Vac and only 50 Vdc.

**IT OUT-RATES EVERY BARRIER STRIP IN THIS DRAWER.** The WEIDU blocks #1204-#1210 and #1203-equivalents are 600V **15 A**. Put this 20 A breaker upstream of one and the strip is the weak link -- it can overheat while the breaker sits happily below its trip point. Size protection to the smallest thing downstream, not to the supply.

**THERMAL, SO IT IS SLOW BY DESIGN.** It trips on accumulated heat, which protects wiring and motors from sustained overload. It will not protect semiconductors from a short -- nothing downstream of it survives on the strength of this breaker alone.

**ONE UNIT ON HAND, and the bag is a 2-pack.** Scott, 2026-09-19: one breaker. Bag label: `mxuteuk 2Pcs 20Amp Circuit Br...terproof Button Caps L1-ls-20A`, ASIN `X002QZHIW1`. The second unit is simply not in hand -- not written off, not searched for. No purchase record has been located and no price is recorded here; an unverified one would need the +40% estimate marker and would be worth nothing.""",
    },
]

STOCK_NOTE = {
    "Barrier Terminal Block, 3-position, 600V 15A, dual row (WEIDU TB-1503)":
        "One unit, in hand 2026-09-19. Stripped of the jumper and wire stub it was "
        "found with before filing, so it is a clean spare. Provenance is kit #283, "
        "not a purchase of its own.",
    "Thermal Circuit Breaker, 20A push-button reset, panel mount (mxuteuk L1-ls-20A)":
        "One unit, counted by Scott 2026-09-19. The bag is a 2-pack; the second unit "
        "is not in hand and is not assumed anywhere.",
}


def too_long():
    bad = []
    for it in ITEMS:
        for f, cap in (("name", 100), ("description", 250), ("keywords", 250)):
            if len(it[f]) > cap:
                bad.append(f"{it['name'][:20]}... {f} {len(it[f])} > {cap}")
    return bad


home = StockLocation.objects.get(pathstring=HOME)
print(f"home: [{home.pk}] {home.pathstring}")
bad = too_long()
for b in bad:
    print(f"  FIELD TOO LONG: {b}")
if bad:
    sys.exit(1)

for it in ITEMS:
    dup = Part.objects.filter(name=it["name"]).first()
    print(f"  {'EXISTS' if dup else 'will create'}  [{it['category']}] {it['name']}")

if not COMMIT:
    print("\nDRY RUN - nothing written. Re-run with --commit.")
    sys.exit(0)

made = {}
for it in ITEMS:
    cat = PartCategory.objects.get(pathstring=it["category"])
    p = Part.objects.filter(name=it["name"]).first()
    if p is None:
        p = Part.objects.create(
            name=it["name"], description=it["description"], category=cat,
            keywords=it["keywords"], notes=it["notes"], default_location=home,
            active=True, purchaseable=True, component=True, salable=False)
    p.refresh_from_db()
    if p.default_location_id != home.pk:
        Part.objects.filter(pk=p.pk).update(default_location=home)
        p.refresh_from_db()

    si = p.stock_items.filter(location=home).first()
    if si is None:
        si = StockItem.objects.create(
            part=p, location=home, quantity=1, notes=STOCK_NOTE[it["name"]])
        si.refresh_from_db()

    made[it["name"]] = p
    print(f"\n#{p.pk} {p.name}")
    print(f"    category         {p.category.pathstring}")
    print(f"    default_location {p.default_location.pathstring}")
    print(f"    stock [{si.pk}] qty {float(si.quantity):g} @ {si.location.pathstring}")

# The breaker's notes point at the strips by pk, so fill that in once it exists.
brk = [p for n, p in made.items() if n.startswith("Thermal")][0]
tb = [p for n, p in made.items() if n.startswith("Barrier")][0]
fixed = tb.notes.replace("#BRK", f"#{brk.pk}")
if fixed != tb.notes:
    Part.objects.filter(pk=tb.pk).update(notes=fixed)
    tb.refresh_from_db()
print(f"\ncross-reference written into #{tb.pk}: {f'#{brk.pk}' in tb.notes}")
