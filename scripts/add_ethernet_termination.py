#!/usr/bin/env python3
"""Catalogue the Cat5e keystone jacks and the Cat6 pass-through RJ45 plugs.

Both photographed 2026-09-19. Read off the packaging and nothing else.

    CAT 5e JACKS                        RJ45 CONNECTOR Pass Through
    Paquete de 25                       CAT6 UN-SHIELDED PASSTHROUGH
    SKU 636 303                         CAT 6, 100 PCS
    No. 5015-WH-25  WHITE               (no brand legible)
    UL listed, resealable bag

KEYSTONES: 15 ON HAND, counted by Scott. The bag says 25 and the bag is
resealable and open -- 15 is what is in it. That gap is the whole reason
"photographs show identity, not quantity" exists: a printed pack size read off
a used bag is the most convincing wrong number available, and it was wrong by
ten here.

PLUGS: NO STOCK ROW. The jar's 100 is a pack size on the same footing and
nobody has counted it.

LOCATION IS A JUDGEMENT CALL, NOT A READING. Both default to B-03, the
ETHERNET & PoE bin created earlier today, because that is what the bin is for
and Scott has been feeding Ethernet items into it all session ("9 1' eth cable
going in there"). Say so plainly rather than presenting it as told.

WHY THESE ARE IN Electronics/Connectors AND NOT .../Adapters WITH THE COUPLER
AND SPLITTER. A plug and a jack are connectors; a coupler and a splitter adapt
between them. The split looks inconsistent browsing the tree and is right on
the merits, and everything here is found by keyword anyway.

THE TOOL SITUATION IS THE REAL FINDING. Searched the whole catalogue for
punchdown, 110 tool, keystone, wall plate, patch panel, krone, IDC: nothing.
These two items need DIFFERENT tools, and the plugs need a specific one.

    itq run scripts/add_ethernet_termination.py [--commit]
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
CATEGORY_PK = 60          # Electronics/Connectors
BIN_PK = 618              # SLN/Laser Area/LW3/LW3-S1/B-03

NO_TOOLS = """**⚠ NOTHING IN THE SHOP TERMINATES THIS.** Searched the whole catalogue 2026-09-19 for punchdown, 110 tool, keystone, wall plate, patch panel, krone, IDC and crimper: **no punchdown tool, no RJ-45 crimper of any kind, no patch panel, no wall plates.**"""

ITEMS = [
    dict(
        prefix="Keystone Jack Cat5e",
        name="Keystone Jack Cat5e RJ45 8P8C, white, 5015-WH",
        desc=("Cat5e RJ-45 keystone jack, white, UL listed. T568A/T568B colour code "
              "on the body. Sold 25 to a resealable bag, SKU 636 303, No. "
              "5015-WH-25. Termination style not verified. 15 on hand."),
        kw=("keystone jack cat5e cat 5e RJ45 rj-45 8P8C white 5015-WH 5015 636303 "
            "punchdown punch down 110 IDC T568A T568B wall plate patch panel "
            "ethernet network termination"),
        qty=15,
        notes="""Cat5e RJ-45 keystone jack, white. Read off the bag 2026-09-19:

    CAT 5e JACKS / Entradas tipo CAT 5e
    Paquete de 25
    SKU 636 303
    No. 5015-WH-25    WHITE / BLANCO
    UL listed, resealable bag

**15 ON HAND, counted by Scott 2026-09-19. The bag says 25.** The bag is resealable and was already open; ten are gone. Recorded here because the gap is the point: a printed pack size read off a used bag is the most convincing wrong number available, and anyone re-checking this row against the packaging will see 25 and be tempted.

**Brand deliberately not recorded.** Nothing on the visible face names a manufacturer. The SKU and part number are enough to re-find it, and a guessed brand reads identically to a read one.

**T568A and T568B are both printed on the jack body** — the usual arrangement, the two schemes on opposite sides. Pick one and use it at *both* ends of every run. A at one end and B at the other makes a crossover; this shop already owns one 10 ft crossover ([#1229]) that is deliberately flagged as a hazard for exactly that confusion.

""" + NO_TOOLS + """ Fifteen jacks and nothing to press them with or land them in.

**Whether these need a 110 punchdown tool or are the tool-less kind was NOT determined.** The bag's photograph is not a reading of the part. Open one and look before buying a tool.

**And a keystone is only half a termination.** The other half is a wall plate, surface box or patch panel, and the catalogue has none. Budget those with the tool, not after it arrives.

**Location is a judgement call:** B-03 is the ETHERNET & PoE bin and this is Ethernet hardware. Nobody said to put it there."""),
    dict(
        prefix="RJ45 Plug Cat6 pass-through",
        name="RJ45 Plug Cat6 pass-through, unshielded",
        desc=("Cat6 UNSHIELDED pass-through RJ-45 plug, 8P8C. Conductors exit the "
              "nose for order-checking before crimping. REQUIRES A PASS-THROUGH "
              "CRIMPER with a flush cutter. Jar of 100; not counted."),
        kw=("RJ45 rj-45 8P8C plug connector pass-through passthrough pass through "
            "cat6 cat 6 unshielded UTP crimp crimper flush cut ethernet network "
            "termination 100 pcs jar"),
        qty=None,
        notes="""Cat6 unshielded **pass-through** RJ-45 plug. Read off the jar 2026-09-19:

    RJ45 CONNECTOR — Pass Through
    CAT6 UN-SHIELDED PASSTHROUGH
    CAT 6      100 PCS
    "Optimal Performance / Easily Identify Wiring Order / Superb Compatibility"

No brand legible on the visible face; not recorded rather than guessed.

**⚠ THESE REQUIRE A PASS-THROUGH CRIMPER — A CONVENTIONAL RJ-45 CRIMPER IS NOT A SUBSTITUTE.** The conductors deliberately protrude through the nose of the plug so the wiring order can be verified before committing. A pass-through crimp tool has an integrated flush cutter that shears them off level with the plug face **in the same squeeze**. An ordinary crimper seats the contacts and leaves the wires standing proud, and trimming them afterwards by hand leaves stubs that snag in a jack and can bridge contacts.

**So the missing tool is now specific, not generic.** "An RJ-45 crimper" does not cover this jar. """ + NO_TOOLS + """

**Why pass-through is the better plug anyway:** you can see the colour order at the nose before you crimp, and the twists stay closer to the contacts than in a conventional plug — which is the part that actually matters at Cat6.

**UNSHIELDED.** There is no shield path through these. They will physically accept shielded cable and silently discard its shield, which is worse than not fitting — an STP run terminated in UTP plugs looks finished and is not grounded.

**NOT VERIFIED: solid vs stranded conductor rating.** Many RJ-45 plugs are specified for one or the other, and the mismatch gives intermittent contact that passes a continuity test and fails under vibration or temperature. Nothing on the jar says which. Pass-through designs are generally tolerant of both, which is a property of the design and not a reading off this product.

**Cat6 plugs on Cat5e cable is fine** and worth knowing, since all four catalogued patch cables have an unknown Cat rating and the keystones are Cat5e.

**NO COUNT. The jar says 100 and that is a PACK SIZE.** Nobody has counted it. The keystone bag next to it said 25 and held 15 — same class of item, same day, and the printed figure was wrong by forty percent.

**Location is a judgement call:** B-03 is the ETHERNET & PoE bin and this is Ethernet hardware. Nobody said to put it there."""),
]


def check(d):
    lim = (("name", d["name"], 100), ("description", d["desc"], 250),
           ("keywords", d["kw"], 250))
    bad = [f"{f}: {len(v)} > {n}" for f, v, n in lim if len(v) > n]
    print(f"  {d['name']}")
    for f, v, n in lim:
        print(f"     {f:12s} {len(v):3d}/{n}")
    return bad


cat = PartCategory.objects.get(pk=CATEGORY_PK)
bin_ = StockLocation.objects.get(pk=BIN_PK)
print(f"category: {cat.pathstring}\nbin:      {bin_.pathstring}\n")

fail = []
for d in ITEMS:
    fail += check(d)
if fail:
    print("\nFIELD TOO LONG — full_clean() would abort:", *fail)
    sys.exit(1)

print("\nexisting matches (idempotency check):")
for d in ITEMS:
    ex = Part.objects.filter(name__startswith=d["prefix"]).first()
    q = "no stock row (uncounted)" if d["qty"] is None else f"qty {d['qty']}"
    print(f"  {d['prefix']:30s} -> {('#%d' % ex.pk) if ex else 'will create':14s} {q}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

made = []
for d in ITEMS:
    ex = Part.objects.filter(name__startswith=d["prefix"]).first()
    if ex is None:
        p = Part.objects.create(name=d["name"], description=d["desc"], category=cat,
                                keywords=d["kw"], notes=d["notes"],
                                default_location=bin_, active=True,
                                purchaseable=True, component=True)
    else:
        p = ex
        Part.objects.filter(pk=p.pk).update(
            name=d["name"], description=d["desc"], category=cat, keywords=d["kw"],
            notes=d["notes"], default_location=bin_)
    p.refresh_from_db()
    si = None
    if d["qty"] is not None:
        si = StockItem.objects.filter(part=p, location=bin_).first()
        if si is None:
            si = StockItem.objects.create(part=p, location=bin_, quantity=d["qty"])
        si.refresh_from_db()
    made.append((p, si, d["qty"]))

print()
for p, si, want in made:
    print(f"#{p.pk} {p.name}")
    print(f"    {p.category.pathstring}   default_location {p.default_location.pathstring}")
    if si is None:
        print("    NO STOCK ROW  <- awaiting a count from Scott")
    else:
        ok = "ok" if float(si.quantity) == float(want) else f"!! wanted {want}"
        print(f"    stock [{si.pk}] qty {si.quantity:g} @ {si.location.pathstring}  {ok}")

ks, plug = made[0][0], made[1][0]
print(f"\nkeystone 15-vs-25 recorded:   {'15 ON HAND, counted by Scott' in ks.notes}")
print(f"keystone tool gap:            {'NOTHING IN THE SHOP TERMINATES THIS' in ks.notes}")
print(f"plug pass-through crimper:    {'A CONVENTIONAL RJ-45 CRIMPER IS NOT A SUBSTITUTE' in plug.notes}")
print(f"plug uncounted stated:        {'NO COUNT. The jar says 100' in plug.notes}")
print(f"plug shielding warning:       {'UNSHIELDED' in plug.notes}")
print(f"B-03 now holds {StockItem.objects.filter(location=bin_).count()} stock rows")
