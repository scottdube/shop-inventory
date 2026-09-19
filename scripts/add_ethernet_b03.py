#!/usr/bin/env python3
"""Stock B-03 with the Ethernet passives and patch cables Scott pulled out.

Scott, 2026-09-19, at the bench:
    "Also two RJ45 splitters and two RJ45 couplers."
    "9 1' eth cable going in there, 3 6' cables a 10' x-over cable and a
     10' patch cable"

All six counts came from Scott, not from the photo, and are therefore counts —
not estimates. The photo established identity only.

WHY FOUR CABLE PARTS AND NOT ONE. Length is the whole reason you reach for one
patch cable over another, so a single "Ethernet Patch Cable" row with qty 13
would answer the only question anyone ever asks it -- "have I got a six-footer?"
-- with a number that cannot be used. And the crossover is not a length variant
at all: it is a different cable that looks identical, which is precisely why it
gets its own row and its own warning.

WHY THE SPLITTERS GET THE LONGEST NOTE. They share a bin with POE-003 (#1223),
a passive 48 V injector, and the pairs a passive splitter steals are exactly the
pairs passive PoE energises. That adjacency was the reason B-03 was created;
putting the two parts in it without writing the interaction down would undo the
point of the move.

Cat rating is NOT recorded for any of these. Nothing legible in the photo gave
it and nobody read a jacket. Guessing Cat5e would be indistinguishable in the
record from having checked.

    itq run scripts/add_ethernet_b03.py [--commit]
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

BIN_PK = 618            # SLN/Laser Area/LW3/LW3-S1/B-03
CAT_CABLE = 119         # Electronics/Cables
CAT_ADAPTER = 127       # Electronics/Connectors/Adapters
POE003 = 1223           # the passive 48 V injector sharing this bin

CABLE_TRAP = """

**Cat rating NOT recorded.** Nothing was read off the jacket — treat the category as unknown, not as Cat5e. Counted by Scott 2026-09-19; the count is a count, not an estimate."""

ITEMS = [
    dict(
        prefix="Ethernet Patch Cable, 1 ft",
        name="Ethernet Patch Cable, 1 ft",
        desc=("Short RJ-45 patch cable, 1 ft / 30 cm, straight-through. Cat rating "
              "not verified. Nine on hand, counted 2026-09-19."),
        kw=("ethernet patch cable rj45 rj-45 8p8c 1ft 1 foot 30cm short "
            "network lan cat5e cat6 straight-through"),
        qty=9, cat=CAT_CABLE,
        notes="""Nine 1 ft RJ-45 patch cables. Counted by Scott 2026-09-19, going into B-03.

**A 1 ft cable is a rack part, not a spare.** This length exists to jump between adjacent ports — switch to patch panel, injector to switch — and is the wrong reach for almost anything else. Nine of them is a stack-wiring kit; do not treat the count as nine general-purpose cables.

**It is also the length that hides a bad crimp.** A one-footer is short enough that a marginal termination still links at gigabit on the bench and drops out at temperature. If a short jumper is in a link that flaps, swap it before suspecting anything else in the path.""" + CABLE_TRAP),
    dict(
        prefix="Ethernet Patch Cable, 6 ft",
        name="Ethernet Patch Cable, 6 ft",
        desc=("RJ-45 patch cable, 6 ft / 1.8 m, straight-through. Cat rating not "
              "verified. Three on hand, counted 2026-09-19."),
        kw=("ethernet patch cable rj45 rj-45 8p8c 6ft 6 foot 1.8m "
            "network lan cat5e cat6 straight-through"),
        qty=3, cat=CAT_CABLE,
        notes="""Three 6 ft RJ-45 patch cables. Counted by Scott 2026-09-19, going into B-03.

**This is the general-purpose length here** — the default to reach for, and the one that will run out first. Three is thin. If Ethernet work continues at the laser wall, this is the row to watch, not the 1 ft stack.""" + CABLE_TRAP),
    dict(
        prefix="Ethernet Patch Cable, 10 ft",
        name="Ethernet Patch Cable, 10 ft",
        desc=("RJ-45 patch cable, 10 ft / 3 m, straight-through. Cat rating not "
              "verified. One on hand, counted 2026-09-19."),
        kw=("ethernet patch cable rj45 rj-45 8p8c 10ft 10 foot 3m "
            "network lan cat5e cat6 straight-through"),
        qty=1, cat=CAT_CABLE,
        notes="""One 10 ft RJ-45 patch cable. Counted by Scott 2026-09-19, going into B-03.

**There is a 10 ft CROSSOVER in this same bin and it looks the same.** See the crossover part's notes — the distinguishing mark, if any, is printed on the jacket and nothing in this record can tell them apart for you. Two identical-looking 10-footers in one bin is the exact condition that wastes an afternoon.""" + CABLE_TRAP),
    dict(
        prefix="Ethernet Crossover Cable, 10 ft",
        name="Ethernet Crossover Cable, 10 ft",
        desc=("RJ-45 CROSSOVER cable, 10 ft / 3 m — TX/RX swapped, NOT a patch "
              "cable. Cat rating not verified. One on hand, counted 2026-09-19."),
        kw=("ethernet crossover cross-over x-over cable rj45 rj-45 8p8c 10ft "
            "10 foot 3m network lan cat5e cat6 mdi mdix"),
        qty=1, cat=CAT_CABLE,
        notes="""One 10 ft RJ-45 **CROSSOVER** cable. Counted by Scott 2026-09-19, going into B-03.

**A crossover is not a patch cable and is physically indistinguishable from one.** Pins 1/2 and 3/6 are swapped end to end. The only way to tell without a tester is whatever is printed on the jacket, and there is a plain 10 ft patch cable in the same bin.

**⚠ TAG THIS ONE PHYSICALLY.** A wrap label or a band at the plug. This is the single cheapest thing that can be done for it, and it is worth doing before the bin is closed — the record cannot reach into the drawer.

**Auto-MDI-X is why this cable is now more dangerous than useful.** Every switch and NIC at SLN negotiates the crossover in silicon, so plugging this into a modern link works fine and teaches you nothing. It stays invisible until it lands in front of the one device that does NOT auto-negotiate — older industrial gear, some managed-switch console ports, a few PLCs — and then the fault presents as "no link", with a cable that tested good in every other socket in the building.

**Keep it anyway.** Direct machine-to-machine on non-negotiating hardware is a real job and nothing else here does it. The hazard is the mix-up, not the cable.""" + CABLE_TRAP),
    dict(
        prefix="RJ45 Inline Coupler, ",
        name="RJ45 Inline Coupler, 8P8C female-female",
        desc=("Straight-through RJ-45 barrel coupler, two 8P8C female jacks, joins "
              "two patch cables end to end. Cat rating not marked. Two on hand."),
        kw=("rj45 rj-45 8p8c inline coupler barrel joiner female female "
            "ethernet network lan extend iMBAPrice modular"),
        qty=2, cat=CAT_ADAPTER,
        notes="""Two straight-through RJ-45 inline couplers, white. Counted by Scott 2026-09-19.

One is loose out of its bag; the other is still sealed and labelled *"iMBAPrice® RJ45 Coupler - Modular Inline Coupler, New"*. Treated as one part at qty 2 — they are the same item and nothing about the packaging makes them non-interchangeable.

**No Cat rating is marked on either, and a coupler's rating is the link's rating.** An unrated or Cat5e coupler in the middle of a Cat6 gigabit run is a real impairment: it breaks the pair twist at the junction and adds two connector interfaces. Short runs will not care. A long run that was already marginal will.

**A coupler is not a repair for a bad crimp.** Joining two cables to route around a damaged plug leaves the damaged plug in the path. Re-terminate instead — though note there is **no RJ-45 crimper in the catalogue** (surveyed 2026-09-19), so re-terminating is not currently an option at SLN.

**It is the right tool for one job: extending a run you cannot re-pull.** Two 6 ft cables and a coupler beat a 12 ft cable you do not have.""" ),
    dict(
        prefix="RJ45 Splitter, passive 2-way",
        name="RJ45 Splitter, passive 2-way",
        desc=("PASSIVE RJ-45 splitter, black. Divides one 4-pair cable into two "
              "2-pair 10/100 links. MUST BE USED IN MATCHING PAIRS. Not a hub. "
              "Two on hand, counted 2026-09-19."),
        kw=("rj45 rj-45 8p8c splitter passive 2-way two way economiser economizer "
            "ethernet network lan 10/100 pair sharing adapter"),
        qty=2, cat=CAT_ADAPTER,
        notes="""Two black passive RJ-45 splitters, bagged together. Counted by Scott 2026-09-19.

**THESE ARE NOT NETWORK SPLITTERS AND THEY WILL NOT LET TWO DEVICES SHARE ONE SWITCH PORT.** That is what the name implies and what they are usually bought for, and it is the one thing they cannot do. There is no electronics inside — it is a passive re-grouping of the eight conductors. Two devices plugged into one of these on a live port will collide and neither will work reliably.

**What they actually do: run TWO 10/100 links down ONE Cat5 cable.**

    switch ──┬─ splitter ═══════ one cable ═══════ splitter ─┬── device A
             └─                                              └── device B

    port 1  ──> pairs 1/2 + 3/6  ──>  port 1 at the far end
    port 2  ──> pairs 4/5 + 7/8  ──>  port 2 at the far end

**They only work in MATCHING PAIRS, one at each end of a single run.** A splitter alone at one end does nothing useful. Two on hand is therefore exactly **one usable run**, not two independent accessories — do not let the pair get separated, and do not count on finding a third.

**10/100 ONLY, at both ends, permanently.** Gigabit needs all four pairs; each link here gets two. Putting one of these in a path caps it at 100 Mbit no matter what the gear at either end supports, and the link will negotiate 100 quietly rather than failing, so the cause is invisible from the far end.

**⚠ NEVER PUT ONE OF THESE IN A RUN CARRYING PASSIVE PoE.** Passive PoE energises pairs **4/5 and 7/8** — and 4/5 + 7/8 is exactly what this splitter routes to its second port as DATA. [POE-003 #1223], the D-Link DWL-P200 base unit, is a passive 48 V injector **living in this same bin**. A splitter downstream of it delivers 48 V into a second device's receive pins. This is the same adjacency hazard that got B-03 created in the first place; it now has two ways to happen, and this one is the less obvious.

Active 802.3af/at is the safer direction but not a licence: Mode B also uses 4/5 + 7/8, and while a compliant PSE will not energise a port it cannot negotiate with, the splitter is what prevents the negotiation from meaning anything downstream. **Keep PoE of every kind out of any run containing one of these.**

**Not verified from the photo:** the exact connector arrangement on each unit, and whether the two are a matched set. They came bagged together, which is how they are sold — but that is an inference, not a reading. Check before relying on them as a pair.""" ),
]


def check(d):
    lim = (("name", d["name"], 100), ("description", d["desc"], 250),
           ("keywords", d["kw"], 250))
    bad = [f"{f}: {len(v)} > {n}" for f, v, n in lim if len(v) > n]
    print(f"  {d['name']}")
    for f, v, n in lim:
        print(f"     {f:12s} {len(v):3d}/{n}")
    return bad


bin_ = StockLocation.objects.get(pk=BIN_PK)
cats = {CAT_CABLE: PartCategory.objects.get(pk=CAT_CABLE),
        CAT_ADAPTER: PartCategory.objects.get(pk=CAT_ADAPTER)}
print(f"bin: {bin_.pathstring}")
for pk, c in cats.items():
    print(f"cat: {c.pathstring}")
print()

fail = []
for d in ITEMS:
    fail += check(d)
if fail:
    print("\nFIELD TOO LONG — full_clean() would abort:", *fail)
    sys.exit(1)

print("\nexisting matches (idempotency check):")
for d in ITEMS:
    ex = Part.objects.filter(name__startswith=d["prefix"]).first()
    print(f"  {d['prefix']:34s} -> {('#%d' % ex.pk) if ex else 'will create'}")

if not COMMIT:
    print("\nDRY RUN — nothing written. Re-run with --commit.")
    sys.exit(0)

made = []
for d in ITEMS:
    cat = cats[d["cat"]]
    ex = Part.objects.filter(name__startswith=d["prefix"]).first()
    if ex is None:
        p = Part.objects.create(name=d["name"], description=d["desc"], category=cat,
                                keywords=d["kw"], notes=d["notes"],
                                default_location=bin_, active=True,
                                purchaseable=True, component=True)
    else:
        p = ex
        Part.objects.filter(pk=p.pk).update(
            name=d["name"], description=d["desc"], category=cat,
            keywords=d["kw"], notes=d["notes"], default_location=bin_)
    p.refresh_from_db()
    si = StockItem.objects.filter(part=p, location=bin_).first()
    if si is None:
        si = StockItem.objects.create(part=p, location=bin_, quantity=d["qty"])
    si.refresh_from_db()
    made.append((p, si, d["qty"]))

print()
for p, si, want in made:
    ok = "ok" if float(si.quantity) == float(want) else f"!! wanted {want}"
    print(f"#{p.pk} {p.name}")
    print(f"    {p.category.pathstring}")
    print(f"    stock [{si.pk}] qty {si.quantity:g} @ {si.location.pathstring}  {ok}")

split = next(p for p, _, _ in made if p.name.startswith("RJ45 Splitter"))
xover = next(p for p, _, _ in made if p.name.startswith("Ethernet Crossover"))
print(f"\nsplitter PoE cross-warning present: {'NEVER PUT ONE OF THESE IN A RUN' in split.notes}")
print(f"splitter cites #1223:               {'#1223' in split.notes}")
print(f"crossover tag-it warning present:   {'TAG THIS ONE PHYSICALLY' in xover.notes}")
print(f"B-03 now holds {StockItem.objects.filter(location=bin_).count()} stock rows")
